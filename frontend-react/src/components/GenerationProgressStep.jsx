import React, { useState, useEffect } from 'react';
import { Loader2, CheckCircle, Download, PlusCircle } from 'lucide-react';

const GenerationProgressStep = ({ 
  progress, 
  progressStatus, 
  progressDetail, 
  isCompleted,
  videoTitle,
  videoUrl,
  orientation,
  resetForm,
  API_BASE,
  addAlert
}) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const downloadVideo = async () => {
    if (!videoUrl) return;
    setIsDownloading(true);
    
    try {
      const response = await fetch(`${API_BASE}${videoUrl}`);
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      const filename = videoUrl.split('/').pop() || `video_${Date.now()}.mp4`;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      addAlert('Video downloaded successfully!', 'success');
    } catch (error) {
      console.error('Download error:', error);
      addAlert('Failed to download video. Please try again.', 'error');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="card-custom">
      <div className="card-header-custom flex items-center">
        <Loader2 className="mr-2 animate-spin" />
        <h4 className="mb-0 text-xl font-semibold">Creating Your Video</h4>
      </div>
      <div className="card-body p-6">
        {!isCompleted ? (
          <div>
            <div className="text-center mb-8">
              <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto mb-4" />
              <h4 className="text-xl font-bold mb-2">{progressStatus}</h4>
              <p className="text-gray-500">{progressDetail}</p>
            </div>
            
            <div className="progress-custom mb-4">
              <div className="progress-bar-custom" style={{ width: `${progress}%` }} />
            </div>
            <div className="text-center font-bold text-primary">
              {progress}%
            </div>
          </div>
        ) : (
          <div>
            <div className="text-center mb-8">
              <CheckCircle className="w-16 h-16 text-success mx-auto mb-4" />
              <h4 className="text-2xl font-bold text-success mb-2">Video Created Successfully!</h4>
              <p className="text-gray-500">Your video "{videoTitle}" is ready.</p>
            </div>
            
            <div className={`video-preview mb-8 ${orientation === 'landscape' ? 'landscape' : ''}`}>
              <video controls autoPlay className="w-full h-full">
                <source src={`${API_BASE}${videoUrl}`} type="video/mp4" />
                Your browser does not support video playback.
              </video>
            </div>
            
            <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
              <button 
                className="btn-primary-custom flex items-center justify-center w-full sm:w-auto"
                onClick={downloadVideo}
                disabled={isDownloading}
              >
                {isDownloading ? (
                  <Loader2 className="mr-2 animate-spin w-5 h-5" />
                ) : (
                  <Download className="mr-2 w-5 h-5" />
                )}
                Download Video
              </button>
              <button 
                className="px-6 py-3 border-2 border-primary text-primary rounded-lg font-semibold flex items-center justify-center hover:bg-primary hover:text-white transition-all w-full sm:w-auto"
                onClick={resetForm}
              >
                <PlusCircle className="mr-2 w-5 h-5" /> Create Another
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GenerationProgressStep;
