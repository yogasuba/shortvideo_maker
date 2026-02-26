import React, { useState } from 'react';
import { Loader2, CheckCircle, Download, PlusCircle, Send,Pencil } from 'lucide-react';
import FacebookShare from './FacebookShare';
import ScheduleModal from './ScheduleModal';
import { OrientationType, AlertType } from '../types';

interface GenerationProgressStepProps {
  progress: number;
  progressStatus: string;
  progressDetail: string;
  isCompleted: boolean;
  videoTitle: string;
  videoUrl: string;
  projectId: string;
  orientation: OrientationType;
  resetForm: () => void;
  API_BASE: string;
  onEdit: () => void;
  addAlert: (message: string, type: AlertType) => void;
}

const GenerationProgressStep: React.FC<GenerationProgressStepProps> = ({ 
  progress, 
  progressStatus, 
  progressDetail, 
  isCompleted,
  videoTitle,
  videoUrl,
  projectId,
  orientation,
  resetForm,
  onEdit,
  API_BASE,
  addAlert
}) => {
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [showScheduleModal, setShowScheduleModal] = useState<boolean>(false);

  const downloadVideo = async () => {
    if (!videoUrl) return;
    
    try {
      // Extract filename from the URL (handles both local and S3 URLs)
      // For S3: https://.../videos/filename.mp4?query...
      // For local: /storage/videos/filename.mp4
      const urlPath = videoUrl.split('?')[0]; // Remove query params
      const filename = urlPath.split('/').pop();
      
      if (!filename) throw new Error('Could not determine filename');
      
      // Use the backend's download proxy to bypass S3 CORS/cache issues
      const downloadUri = `${API_BASE}/api/download/${filename}`;
      
      // Simple link click for download is more reliable than fetch+blob for large video files
      const link = document.createElement('a');
      link.href = downloadUri;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      addAlert('Download started!', 'success');
    } catch (error) {
      console.error('Download error:', error);
      addAlert('Failed to prepare download. Please try again.', 'error');
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
                <source src={videoUrl.startsWith('http') ? videoUrl : `${API_BASE}${videoUrl}`} type="video/mp4" />
                Your browser does not support video playback.
              </video>
            </div>
            
            <div className="flex flex-col sm:flex-row justify-center items-center gap-4 mb-8">
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
                className="btn-primary-custom flex items-center justify-center w-full sm:w-auto bg-pink-600 hover:bg-pink-700"
                onClick={() => setShowScheduleModal(true)}
              >
                <Send className="mr-2 w-5 h-5" /> Schedule to Socials
              </button>

              <button 
                className="px-6 py-3 border-2 border-primary text-primary rounded-lg font-semibold flex items-center justify-center hover:bg-primary hover:text-white transition-all w-full sm:w-auto"
                onClick={resetForm}
              >
                <PlusCircle className="mr-2 w-5 h-5" /> Create Another
              </button>
              <button 
                className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg font-semibold flex items-center justify-center hover:bg-gray-200 transition-all w-full sm:w-auto"
                onClick={onEdit}
              >
                <Pencil className="mr-2 w-5 h-5" /> Edit Settings
              </button>
            </div>

            <FacebookShare 
              projectId={projectId}
              videoUrl={videoUrl}
              videoTitle={videoTitle}
              API_BASE={API_BASE}
              addAlert={addAlert}
            />
            
            {showScheduleModal && (
              <ScheduleModal 
                videoId={projectId}
                onClose={() => setShowScheduleModal(false)}
                onSuccess={() => addAlert('Post scheduled successfully!', 'success')}
                API_BASE={API_BASE}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GenerationProgressStep;
