import React, { useState, useEffect } from 'react';
import { Facebook, Calendar, Send, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { Integration, ApiResponse, AlertType } from '../types';

interface FacebookShareProps {
  projectId: string;
  videoUrl: string;
  videoTitle: string;
  API_BASE: string;
  addAlert: (message: string, type: AlertType) => void;
}

const FacebookShare: React.FC<FacebookShareProps> = ({ projectId, videoUrl, videoTitle, API_BASE, addAlert }) => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [selectedIntegration, setSelectedIntegration] = useState<string>('');
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [isPosting, setIsPosting] = useState<boolean>(false);
  const [isScheduling, setIsScheduling] = useState<boolean>(false);
  const [caption, setCaption] = useState<string>(videoTitle || '');
  const [scheduleTime, setScheduleTime] = useState<string>('');
  const [postStatus, setPostStatus] = useState<'success' | 'error' | null>(null); // 'success', 'error'
  const [showSchedule, setShowSchedule] = useState<boolean>(false);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/facebook/integrations`);
      const data: ApiResponse<Integration[]> = await response.json();
      if (data.success && data.data) {
        setIntegrations(data.data);
        if (data.data.length > 0) {
          setSelectedIntegration(data.data[0].id);
        }
      }
    } catch (error) {
      console.error('Error fetching integrations:', error);
    }
  };

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      const response = await fetch(`${API_BASE}/api/facebook/auth-url`);
      const data: ApiResponse<{ url: string }> = await response.json();
      if (data.success && data.data?.url) {
        window.location.href = data.data.url;
      }
    } catch (error) {
      addAlert('Failed to get connection URL', 'error');
      setIsConnecting(false);
    }
  };

  const handlePostNow = async () => {
    if (!selectedIntegration) {
      addAlert('Please select a Facebook page first', 'error');
      return;
    }

    setIsPosting(true);
    const formData = new FormData();
    formData.append('project_id', projectId);
    formData.append('integration_id', selectedIntegration);
    formData.append('caption', caption);

    try {
      const response = await fetch(`${API_BASE}/api/facebook/post-now`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (data.success) {
        setPostStatus('success');
        addAlert('Successfully posted to Facebook!', 'success');
      } else {
        throw new Error(data.detail || 'Failed to post');
      }
    } catch (error) {
      setPostStatus('error');
      addAlert(`Error posting to Facebook: ${(error as Error).message}`, 'error');
    } finally {
      setIsPosting(false);
    }
  };

  const handleSchedule = async () => {
    if (!selectedIntegration) {
      addAlert('Please select a Facebook page first', 'error');
      return;
    }
    if (!scheduleTime) {
      addAlert('Please select a date and time', 'error');
      return;
    }

    setIsScheduling(true);
    const formData = new FormData();
    formData.append('project_id', projectId);
    formData.append('integration_id', selectedIntegration);
    formData.append('schedule_time', new Date(scheduleTime).toISOString());
    formData.append('caption', caption);

    try {
      const response = await fetch(`${API_BASE}/api/facebook/schedule`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (data.success) {
        setPostStatus('success');
        addAlert('Post scheduled successfully!', 'success');
        setShowSchedule(false);
      } else {
        throw new Error(data.detail || 'Failed to schedule');
      }
    } catch (error) {
      addAlert(`Error scheduling post: ${(error as Error).message}`, 'error');
    } finally {
      setIsScheduling(false);
    }
  };

  if (integrations.length === 0) {
    return (
      <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
        <div className="flex items-center mb-4">
          <Facebook className="text-blue-600 mr-2" />
          <h5 className="text-lg font-bold">Post to Facebook</h5>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Connect your Facebook page to instantly share your generated reels.
        </p>
        <button 
          onClick={handleConnect}
          disabled={isConnecting}
          className="btn-primary-custom flex items-center justify-center"
        >
          {isConnecting ? <Loader2 className="animate-spin mr-2" /> : <Facebook className="mr-2" />}
          Connect Facebook Page
        </button>
      </div>
    );
  }

  return (
    <div className="mt-8 p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Facebook className="text-blue-600 mr-2" size={24} />
          <h5 className="text-lg font-bold">Share on Facebook</h5>
        </div>
        <button 
          onClick={handleConnect}
          className="text-xs text-blue-600 hover:underline"
        >
          Connect another page
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Select Page</label>
          <select 
            value={selectedIntegration}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedIntegration(e.target.value)}
            className="w-full p-2 border rounded-lg bg-gray-50 dark:bg-gray-700"
          >
            {integrations.map(int => (
              <option key={int.id} value={int.id}>{int.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Caption</label>
          <textarea 
            value={caption}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCaption(e.target.value)}
            className="w-full p-3 border rounded-lg bg-gray-50 dark:bg-gray-700 h-24"
            placeholder="Write a caption for your post..."
          />
        </div>

        {showSchedule && (
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-dashed border-gray-300">
            <label className="block text-sm font-medium mb-2 flex items-center">
              <Calendar size={14} className="mr-1" /> Pick Date & Time (UTC)
            </label>
            <input 
              type="datetime-local"
              value={scheduleTime}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setScheduleTime(e.target.value)}
              className="w-full p-2 border rounded-lg mb-3"
              min={new Date().toISOString().slice(0, 16)}
            />
            <div className="flex gap-2">
              <button 
                onClick={handleSchedule}
                disabled={isScheduling}
                className="btn-primary-custom flex-1 text-sm py-2"
              >
                {isScheduling ? <Loader2 size={16} className="animate-spin mr-2" /> : <Calendar size={16} className="mr-2" />}
                Confirm Schedule
              </button>
              <button 
                onClick={() => setShowSchedule(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {!showSchedule && (
          <div className="flex flex-col sm:flex-row gap-3">
            <button 
              onClick={handlePostNow}
              disabled={isPosting}
              className="btn-primary-custom flex-1 flex items-center justify-center py-2"
            >
              {isPosting ? <Loader2 size={18} className="animate-spin mr-2" /> : <Send size={18} className="mr-2" />}
              Post Now
            </button>
            <button 
              onClick={() => setShowSchedule(true)}
              className="flex-1 px-4 py-2 border-2 border-blue-600 text-blue-600 rounded-lg font-semibold flex items-center justify-center hover:bg-blue-600 hover:text-white transition-all"
            >
              <Calendar size={18} className="mr-2" />
              Schedule Post
            </button>
          </div>
        )}

        {postStatus === 'success' && (
          <div className="flex items-center text-success mt-2 text-sm">
            <CheckCircle2 size={16} className="mr-1" /> Post processed successfully!
          </div>
        )}
      </div>
    </div>
  );
};

export default FacebookShare;
