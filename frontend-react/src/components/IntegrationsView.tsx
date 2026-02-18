import React, { useState, useEffect } from 'react';
import { Share2, Plus, Loader2, RefreshCw, Trash2, ExternalLink } from 'lucide-react';
import { PostizIntegration, ApiResponse } from '../types';
import PlatformSelector from './PlatformSelector';
import ConnectAccountModal from './ConnectAccountModal';

interface IntegrationsViewProps {
  API_BASE: string;
  addAlert: (message: string, type: 'success' | 'error' | 'info' | 'warning') => void;
}

const IntegrationsView: React.FC<IntegrationsViewProps> = ({ API_BASE, addAlert }) => {
  const [integrations, setIntegrations] = useState<PostizIntegration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showConnectModal, setShowConnectModal] = useState(false);

  const fetchIntegrations = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/postiz/integrations?force_refresh=true`);
      const data: ApiResponse<PostizIntegration[]> = await response.json();
      if (data.success && data.data) {
        setIntegrations(data.data);
      } else {
        addAlert(data.detail || 'Failed to fetch integrations', 'error');
      }
    } catch (error) {
       addAlert('Network error while fetching integrations', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleDeleteIntegration = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/postiz/integrations/${id}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (data.success) {
        addAlert('Account disconnected successfully', 'success');
        fetchIntegrations();
      } else {
        addAlert(data.detail || 'Failed to disconnect account', 'error');
      }
    } catch (error) {
      addAlert('Network error while disconnecting account', 'error');
    }
  };

  return (
    <div className="animate-fade-in pb-12">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-800">Social Integrations</h2>
          <p className="text-gray-500 mt-1">Connect and manage your social media accounts via Postiz.</p>
        </div>
        <div className="flex gap-2">
            <button 
                onClick={fetchIntegrations}
                disabled={isLoading}
                className="p-2 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
                title="Refresh Integrations"
            >
                <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button 
                onClick={() => setShowConnectModal(true)}
                className="btn-primary-custom flex items-center"
            >
                <Plus className="w-5 h-5 mr-2" /> Connect New
            </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
        <div className="p-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-6 flex items-center">
            <Share2 className="w-5 h-5 mr-2 text-indigo-600" />
            Connected Channels
          </h3>

          <PlatformSelector 
            platforms={integrations}
            selected={[]} // No selection in management view
            onChange={() => {}} // Read-only in management view
            isLoading={isLoading}
            onConnect={() => setShowConnectModal(true)}
            onDelete={handleDeleteIntegration}
            API_BASE={API_BASE}
          />
          
          {integrations.length > 0 && (
              <div className="mt-12 p-6 bg-gray-50 rounded-xl border border-gray-100">
                  <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4">Management Info</h4>
                  <p className="text-sm text-gray-600 leading-relaxed">
                      Your accounts are connected headless through Postiz. All posts scheduled in Faceless Videos will use these channels. 
                      To disconnect or manage advanced settings, you can also use the Postiz dashboard directly if needed.
                  </p>
              </div>
          )}
        </div>
      </div>

      {showConnectModal && (
        <ConnectAccountModal 
          isOpen={showConnectModal}
          onClose={() => setShowConnectModal(false)}
          onAccountConnected={fetchIntegrations}
          API_BASE={API_BASE}
        />
      )}
    </div>
  );
};

export default IntegrationsView;
