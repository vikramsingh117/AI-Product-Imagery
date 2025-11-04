import os
import cv2
import json
import tempfile
import shutil
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import google.generativeai as genai
from PIL import Image
import base64
import io

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# Directory to persist enhanced images
ENHANCED_DIR = os.path.join(os.getcwd(), 'enhanced_images')
os.makedirs(ENHANCED_DIR, exist_ok=True)


def download_video(url, output_dir):
    print(f"[download] start: {url}")
    ydl_opts = {
        'format': 'best[height<=720]',
        'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        print(f"[download] complete: {filename}")
        for ext in ['mp4', 'webm', 'mkv']:
            potential_file = filename.rsplit('.', 1)[0] + '.' + ext
            if os.path.exists(potential_file):
                print(f"[download] located file: {potential_file}")
                return potential_file
        return filename


def extract_frames(video_path, interval_seconds=2):
    print(f"[frames] extracting every {interval_seconds}s from: {video_path}")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * interval_seconds)
    frames = []
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append({
                'frame_number': frame_count,
                'timestamp': frame_count / fps,
                'image': Image.fromarray(frame_rgb)
            })
        frame_count += 1
    cap.release()
    print(f"[frames] extracted: {len(frames)} frames (fps={fps:.2f})")
    return frames


def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode()


def generate_enhanced_image_with_flash(image_path, prompt):
    try:
        try:
            print("[enhance] importing google.genai client...")
            from google import genai as genai_client  # lazy import
        except Exception:
            print("[enhance] google-genai not available")
            return None
        base_prompt = prompt or "Create a clean, professional studio product photo with soft shadows on a neutral background."
        print(f"[enhance] opening image: {image_path}")
        img = Image.open(image_path).convert("RGB")
        print("[enhance] creating genai client...")
        client = genai_client.Client(api_key=GEMINI_API_KEY)
        print("[enhance] calling generate_content (primary prompt)...")
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[base_prompt, img],
        )
        print(f"[enhance] response received: type={type(response).__name__}")
        candidates = getattr(response, "candidates", []) or []
        print(f"[enhance] candidates count: {len(candidates)}")
        if not candidates:
            print("[enhance] no candidates returned")
        for i, cand in enumerate(candidates, start=1):
            parts = getattr(cand.content, "parts", []) or []
            print(f"[enhance] candidate {i} parts: {len(parts)}")
            for j, part in enumerate(parts, start=1):
                # Text part - log and continue
                if getattr(part, "text", None):
                    print(f"[enhance] cand {i} part {j} text: {part.text[:120]}")
                    continue
                # Inline image data
                inline = getattr(part, "inline_data", None)
                data = getattr(inline, "data", None) if inline else None
                if data:
                    from io import BytesIO
                    bio = BytesIO(data)
                    out_img = Image.open(bio).convert("RGB")
                    out_buf = io.BytesIO()
                    out_img.save(out_buf, format="JPEG", quality=92)
                    return base64.b64encode(out_buf.getvalue()).decode()
        # Retry once with simpler prompt if nothing returned
        print("[enhance] retrying with simpler prompt")
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=["Studio product photo, neutral background.", img],
        )
        print(f"[enhance] retry response type={type(response).__name__}")
        candidates = getattr(response, "candidates", []) or []
        print(f"[enhance] retry candidates: {len(candidates)}")
        for i, cand in enumerate(candidates, start=1):
            parts = getattr(cand.content, "parts", []) or []
            print(f"[enhance] retry cand {i} parts: {len(parts)}")
            for j, part in enumerate(parts, start=1):
                inline = getattr(part, "inline_data", None)
                data = getattr(inline, "data", None) if inline else None
                if data:
                    from io import BytesIO
                    bio = BytesIO(data)
                    out_img = Image.open(bio).convert("RGB")
                    out_buf = io.BytesIO()
                    out_img.save(out_buf, format="JPEG", quality=92)
                    return base64.b64encode(out_buf.getvalue()).decode()
        return None
    except Exception:
        import traceback
        print("[enhance] exception while generating image")
        traceback.print_exc()
        return None


def build_generation_prompt_from_frame(image_path, product_name: str | None) -> str | None:
    try:
        subject = product_name or 'the product'
        instruction = (
            "You will see a video frame showing a product. "
            f"Identify {subject} and write a SINGLE concise text-to-image prompt to generate a photorealistic studio shot. "
            "Include: product name and color, materials/finish, angle (e.g., 3/4 view), framing (full product, centered), "
            "lighting (soft studio), neutral gradient background, soft shadow, no people, no text, no extra objects. "
            "Return ONLY JSON: {\"prompt\": \"...\"}"
        )
        img = Image.open(image_path).convert("RGB")
        print("[prompt-gen] calling analysis model for generation prompt...")
        resp = model.generate_content([instruction, img])
        text = (resp.text or '').strip()
        # Extract JSON if wrapped
        if '```' in text:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                text = text[start:end]
        try:
            data = json.loads(text)
            prompt = data.get('prompt')
            if prompt:
                print(f"[prompt-gen] prompt length: {len(prompt)}")
                return prompt
        except Exception:
            pass
        print("[prompt-gen] failed to parse prompt JSON")
        return None
    except Exception:
        import traceback
        print("[prompt-gen] exception while building prompt")
        traceback.print_exc()
        return None


def generate_image_with_imagen_from_text(prompt: str) -> str | None:
    try:
        try:
            print("[imagen] importing google.genai client...")
            from google import genai as genai_client
            from google.genai import types as genai_types
        except Exception:
            print("[imagen] google-genai not available")
            return None
        client = genai_client.Client(api_key=GEMINI_API_KEY)
        print("[imagen] calling generate_images (imagen-4.0-generate-001)...")
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt,
            config=genai_types.GenerateImagesConfig(number_of_images=1),
        )
        images = getattr(response, 'generated_images', []) or []
        print(f"[imagen] generated_images count: {len(images)}")
        for gi in images:
            out_img = gi.image.convert('RGB')
            out_buf = io.BytesIO()
            out_img.save(out_buf, format='JPEG', quality=92)
            return base64.b64encode(out_buf.getvalue()).decode()
        return None
    except Exception:
        import traceback
        print("[imagen] exception while generating from text")
        traceback.print_exc()
        return None


def analyze_frames(frames, product_title=None):
    products = {}
    best_frames = {}
    sampled_frames = frames[::5] if len(frames) > 5 else frames
    if len(sampled_frames) > 50:
        step = len(sampled_frames) // 50
        sampled_frames = sampled_frames[::step][:50]
    print(f"[analyze] sampled {len(sampled_frames)} frames (of {len(frames)})")
    
    if product_title:
        analysis_prompt = f"""Analyze this video frame from a product review/unboxing video.

You are looking specifically for: {product_title}

Only identify and rate frames that show this specific product. Ignore other objects in the background.

For the product "{product_title}" visible in this frame:
1. Confirm this is the correct product (must match "{product_title}")
2. Rate the quality (1-10) where 10 is perfect:
   - 9-10: Product is crystal clear, well-lit, fully visible, professional shot
   - 7-8: Product is clear and visible, good lighting
   - 5-6: Product is somewhat visible but not optimal
   - 1-4: Product is blurry, poorly lit, or mostly obscured

Return ONLY valid JSON in this exact format:
{{
  "products": [
    {{
      "name": "{product_title}",
      "quality_score": 8,
      "visible": true
    }}
  ]
}}

If the product "{product_title}" is NOT clearly visible in this frame, return: {{"products": []}}"""
    else:
        analysis_prompt = """Analyze this video frame from a product review/unboxing video.

For EACH product visible in this frame:
1. Identify the product title/name clearly (use the exact product name, brand, and model if visible)
2. Rate the quality (1-10) where 10 is perfect:
   - 9-10: Product is crystal clear, well-lit, fully visible, professional shot
   - 7-8: Product is clear and visible, good lighting
   - 5-6: Product is somewhat visible but not optimal
   - 1-4: Product is blurry, poorly lit, or mostly obscured

Return ONLY valid JSON in this exact format:
{
  "products": [
    {
      "name": "Product Title/Name (e.g., iPhone 15 Pro, Samsung Galaxy Watch)",
      "quality_score": 8,
      "visible": true
    }
  ]sampled_frames
}

If NO products are clearly visible, return: {"products": []}"""

    for idx, frame_data in enumerate(sampled_frames, start=1):
        frame_num = frame_data['frame_number']
        timestamp = frame_data['timestamp']
        image = frame_data['image']
        print(f"[analyze] frame {idx}/{len(sampled_frames)} -> #{frame_num} @ {timestamp:.2f}s")
        analyze_frames
        try:
            analysis_image = image
            max_size = 1024
            if analysis_image.width > max_size or analysis_image.height > max_size:
                analysis_image = analysis_image.copy()
                analysis_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            response = model.generate_content([analysis_prompt, analysis_image])
            response_text = response.text
            print(f"[analyze] model responded ({len(response_text)} chars)")
            
            cleaned_text = response_text.strip()
            if '```json' in cleaned_text:
                json_start = cleaned_text.find('```json') + 7
                json_end = cleaned_text.find('```', json_start)
                if json_end > json_start:
                    cleaned_text = cleaned_text[json_start:json_end].strip()
            elif '```' in cleaned_text:
                json_start = cleaned_text.find('```') + 3
                json_end = cleaned_text.find('```', json_start)
                if json_end > json_start:
                    cleaned_text = cleaned_text[json_start:json_end].strip()
            
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                cleaned_text = cleaned_text[json_start:json_end]
            
            try:
                result = json.loads(cleaned_text)
                detected = result.get('products', [])
                print(f"[analyze] parsed products: {len(detected)}")
                for product_info in detected:
                    product_name = product_info.get('name', 'Unknown Product')
                    quality_score = product_info.get('quality_score', 0)
                    
                    # If a product_title is provided, prefer matches but don't drop non-matches
                    if product_title and product_title.lower() not in product_name.lower():
                        quality_score = max(0, quality_score - 3)
                    
                    if product_name not in best_frames:
                        best_frames[product_name] = {
                            'frame_number': frame_num,
                            'timestamp': timestamp,
                            'quality_score': quality_score,
                            'image_base64': image_to_base64(image)
                        }
                        products[product_name] = {
                            'title': product_name,
                            'name': product_name,
                            'best_frame': best_frames[product_name]
                        }
                        print(f"[analyze] new product '{product_name}' score={quality_score}")
                    else:
                        if quality_score > best_frames[product_name]['quality_score']:
                            best_frames[product_name] = {
                                'frame_number': frame_num,
                                'timestamp': timestamp,
                                'quality_score': quality_score,
                                'image_base64': image_to_base64(image)
                            }
                            products[product_name]['best_frame'] = best_frames[product_name]
                            products[product_name]['title'] = product_name
                            print(f"[analyze] improved '{product_name}' score={quality_score}")
            except json.JSONDecodeError:
                print("[analyze] json parse failed; skipping frame")
                continue
        except Exception:
            print("[analyze] model call failed; skipping frame")
            continue
    
    prod_list = list(products.values())
    print(f"[analyze] total unique products: {len(prod_list)}")
    return {'products': prod_list}


@app.route('/api/process-video', methods=['POST'])
def process_video():
    data = request.get_json()
    youtube_url = data.get('url')
    product_title = data.get('product_title')
    
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        video_path = download_video(youtube_url, temp_dir)
        if not os.path.exists(video_path):
            return jsonify({'error': 'Failed to download video'}), 500
        
        frames = extract_frames(video_path, interval_seconds=5)
        if not frames:
            return jsonify({'error': 'No frames extracted from video'}), 500
        
        analysis_result = analyze_frames(frames, product_title=product_title)
        
        if 'error' in analysis_result:
            return jsonify(analysis_result), 500
        
        products = analysis_result.get('products', [])
        products_sorted = sorted(products, key=lambda x: x.get('best_frame', {}).get('quality_score', 0), reverse=True)
        print(f"[result] products sorted: {len(products_sorted)}")

        # Enhance the top product's best frame using flash image model (optional if available)
        if products_sorted:
            top_product = products_sorted[0]
            bf = top_product.get('best_frame', {})
            img_b64 = bf.get('image_base64')
            if img_b64:
                try:
                    raw = base64.b64decode(img_b64)
                    best_path = os.path.join(temp_dir, 'best_frame.jpg')
                    with open(best_path, 'wb') as f:
                        f.write(raw)
                    print(f"[enhance] saved best frame: {best_path}")
                    product_name_for_gen = (top_product.get('title') or top_product.get('name') or 'the product')
                    print(f"[enhance] building text prompt from best frame for: {product_name_for_gen}")
                    gen_prompt = build_generation_prompt_from_frame(best_path, product_name_for_gen)
                    if not gen_prompt:
                        # Fallback simple prompt
                        gen_prompt = (
                            f"Photorealistic studio shot of {product_name_for_gen}, centered, full product, "
                            f"neutral gradient background, soft shadow, high detail, no text, no extra objects."
                        )
                    print("[enhance] calling Imagen text-to-image...")
                    enhanced_b64 = generate_image_with_imagen_from_text(gen_prompt)
                    if enhanced_b64:
                        top_product['enhanced_image_base64'] = enhanced_b64
                        # Persist enhanced image to disk
                        import time, re
                        title_for_name = (top_product.get('title') or top_product.get('name') or 'product')
                        slug = re.sub(r'[^a-zA-Z0-9_-]+', '-', title_for_name).strip('-').lower()
                        fname = f"{slug}-{int(time.time())}.jpg"
                        out_path = os.path.join(ENHANCED_DIR, fname)
                        with open(out_path, 'wb') as outf:
                            outf.write(base64.b64decode(enhanced_b64))
                        top_product['enhanced_image_path'] = out_path
                        print(f"[enhance] saved enhanced: {out_path}")
                    else:
                        print("[enhance] no enhanced image returned")
                except Exception:
                    print("[enhance] failed to save or generate enhanced image")
                    pass

        return jsonify({
            'success': True,
            'total_frames_analyzed': len(frames),
            'products': products_sorted
        })
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
