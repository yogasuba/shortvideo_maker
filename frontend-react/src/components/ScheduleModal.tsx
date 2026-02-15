import React, { useState, useEffect } from 'react';
import { X, Calendar as CalendarIcon, Clock, Send, Loader2 } from 'lucide-react';
import PlatformSelector from './PlatformSelector';
import CaptionEditor from './CaptionEditor';
import ConnectAccountModal from './ConnectAccountModal';
import { PostizIntegration, ApiResponse } from '../types';

interface ScheduleModalProps {
  videoId: string;
  onClose: () => void;
  onSuccess: () => void;
  API_BASE: string;
}

const ScheduleModal: React.FC<ScheduleModalProps> = ({ videoId, onClose, onSuccess, API_BASE }) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [platforms, setPlatforms] = useState<PostizIntegration[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [caption, setCaption] = useState('');
  const [scheduleTime, setScheduleTime] = useState<string>(''); // ISO string
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConnectModal, setShowConnectModal] = useState(false);

  // Fetch available platforms on mount
  const fetchPlatforms = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/postiz/integrations?force_refresh=true`);
      const data: ApiResponse<PostizIntegration[]> = await response.json();
      
      if (data.success && data.data) {
        setPlatforms(data.data);
      } else {
        setError(data.detail || 'Failed to load platforms');
      }
    } catch (err) {
      setError('Failed to connect to backend');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPlatforms();
  }, []);

  const handleSchedule = async () => {
    if (selectedPlatforms.length === 0) {
      setError('Please select at least one platform');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        video_id: videoId,
        caption: caption,
        platform_ids: selectedPlatforms,
        schedule_time: scheduleTime ? new Date(scheduleTime).toISOString() : null
      };

      const response = await fetch(`${API_BASE}/api/postiz/upload-and-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data.success) {
        onSuccess();
        onClose();
      } else {
        setError(data.detail || 'Scheduling failed');
      }
    } catch (err) {
      setError('Network error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Get current date-time for min attribute
  const now = new Date();
  const minDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto flex flex-col">
        
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b sticky top-0 bg-white z-10">
          <h2 className="text-xl font-bold text-gray-800 flex items-center">
            <Send className="w-5 h-5 mr-2 text-indigo-600" />
            Schedule to Social Media
          </h2>
          <button 
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-6 h-6 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-8 flex-grow">
          
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          {/* Section 1: Platforms */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">
              1. Select Platforms
            </h3>
            <PlatformSelector 
              platforms={platforms}
              selected={selectedPlatforms}
              onChange={setSelectedPlatforms}
              isLoading={isLoading}
              onConnect={() => setShowConnectModal(true)}
              API_BASE={API_BASE}
            />
          </section>

          {/* Section 2: Caption */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3">
              2. Draft Content
            </h3>
            <CaptionEditor 
              value={caption}
              onChange={setCaption}
            />
          </section>

          {/* Section 3: Time */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-3 flex items-center">
              3. Schedule Time <span className="ml-2 text-xs font-normal text-gray-500">(Optional - Leave empty to post now)</span>
            </h3>
            <div className="flex items-center space-x-4">
              <div className="relative flex-grow max-w-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <CalendarIcon className="h-5 w-5 text-gray-400" />
                </div>
                <input 
                  type="datetime-local" 
                  className="pl-10 block w-full border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 border"
                  min={minDateTime}
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                />
              </div>
            </div>
          </section>

        </div>

        {/* Footer */}
        <div className="p-6 border-t bg-gray-50 sticky bottom-0 rounded-b-xl flex justify-end space-x-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-white transition-colors"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          
          <button 
            onClick={handleSchedule}
            disabled={isSubmitting || selectedPlatforms.length === 0}
            className={`
              px-6 py-2 rounded-lg text-white font-medium flex items-center
              ${isSubmitting || selectedPlatforms.length === 0 
                ? 'bg-indigo-400 cursor-not-allowed' 
                : 'btn-primary-custom hover:bg-indigo-700'}
            `}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Scheduling...
              </>
            ) : scheduleTime ? 'Schedule Post' : 'Post Now'}
          </button>
        </div>

      </div>

      {showConnectModal && (
        <ConnectAccountModal 
          isOpen={showConnectModal}
          onClose={() => setShowConnectModal(false)}
          onAccountConnected={fetchPlatforms}
          API_BASE={API_BASE}
        />
      )}
    </div>
  );
};

export default ScheduleModal;
