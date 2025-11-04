'use client';

import { useState } from 'react';
import axios from 'axios';

interface Product {
  name: string;
  title?: string;
  best_frame: {
    frame_number: number;
    timestamp: number;
    quality_score: number;
    image_base64: string;
  };
  enhanced_image_base64?: string;
}

interface ProcessResponse {
  success: boolean;
  total_frames_analyzed: number;
  products: Product[];
  error?: string;
}

export default function Home() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!youtubeUrl.trim()) {
      setError('Please enter a YouTube URL');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await axios.post(
        'http://localhost:5000/api/process-video',
        { url: youtubeUrl }
      );
      
      setResults(response.data);
    } catch (err: any) {
      setError(
        err.response?.data?.error || 
        'Failed to process video. Make sure the backend is running.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen p-8 bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Product Image Extractor
          </h1>
          <p className="text-gray-600">
            Extract the best product shots from YouTube videos using AI
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label 
                htmlFor="youtube-url" 
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                YouTube Video URL
              </label>
              <input
                id="youtube-url"
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loading ? 'Processing...' : 'Extract Product Images'}
            </button>
          </form>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">
              Processing video... This may take a minute.
            </p>
          </div>
        )}

        {results && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Analysis Results
              </h2>
              <p className="text-gray-600 mb-4">
                Analyzed {results.total_frames_analyzed} frames
              </p>
              
              {results.products.length === 0 ? (
                <p className="text-gray-500">No products detected in the video.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {results.products.map((product, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
                    >
                      <div className="p-4 bg-gray-50">
                        <h3 className="font-semibold text-gray-900 mb-2">
                          {product.title || product.name}
                        </h3>
                        <div className="text-sm text-gray-600 space-y-1">
                          <p>Quality Score: {product.best_frame.quality_score}/10</p>
                          <p>Frame: {product.best_frame.frame_number}</p>
                          <p>Timestamp: {Math.floor(product.best_frame.timestamp)}s</p>
                        </div>
                      </div>
                      <div className="bg-gray-100 p-4 space-y-3">
                        <img
                          src={`data:image/jpeg;base64,${product.best_frame.image_base64}`}
                          alt={product.title || product.name}
                          className="w-full h-auto rounded-md"
                        />
                        {product.enhanced_image_base64 && (
                          <div>
                            <p className="text-sm text-gray-700 mb-2">Enhanced</p>
                            <img
                              src={`data:image/jpeg;base64,${product.enhanced_image_base64}`}
                              alt={(product.title || product.name) + ' (enhanced)'}
                              className="w-full h-auto rounded-md border border-blue-200"
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

