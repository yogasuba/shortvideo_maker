import React, { useState } from 'react';
import { 
  X, Facebook, Instagram, Youtube, Twitter, Linkedin, 
  Ghost, MessageSquare, Share2, Music, Send, Hash, 
  Slack, Disc, Globe
} from 'lucide-react';

interface ConnectAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccountConnected: () => void;
  API_BASE: string;
}

const ConnectAccountModal: React.FC<ConnectAccountModalProps> = ({ 
  isOpen, onClose, onAccountConnected, API_BASE 
}) => {
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Comprehensive list of platforms supported by Postiz
  const platforms = [
    { id: 'facebook', name: 'Facebook', icon: Facebook, color: 'bg-blue-600' },
    { id: 'instagram', name: 'Instagram', icon: Instagram, color: 'bg-pink-600' },
    { id: 'youtube', name: 'YouTube', icon: Youtube, color: 'bg-red-600' },
    { id: 'twitter', name: 'X / Twitter', icon: Twitter, color: 'bg-black' },
    { id: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'bg-blue-700' },
    { id: 'tiktok', name: 'TikTok', icon: Music, color: 'bg-black' },
    { id: 'pinterest', name: 'Pinterest', icon: Hash, color: 'bg-red-700' },
    { id: 'reddit', name: 'Reddit', icon: Share2, color: 'bg-orange-600' },
    { id: 'threads', name: 'Threads', icon: Hash, color: 'bg-black' },
    { id: 'discord', name: 'Discord', icon: Disc, color: 'bg-indigo-600' },
    { id: 'slack', name: 'Slack', icon: Slack, color: 'bg-purple-600' },
    { id: 'mastodon', name: 'Mastodon', icon: Globe, color: 'bg-indigo-700' },
  ];

  const [pagesToConnect, setPagesToConnect] = useState<any[] | null>(null);
  const [currentIntegrationId, setCurrentIntegrationId] = useState<string | null>(null);
  const [connectState, setConnectState] = useState<string | null>(null);

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    setError(null);
    setPagesToConnect(null);
    
    try {
      // 1. Get OAuth URL from backend (Headless flow)
      const callbackUrl = encodeURIComponent(window.location.origin);
      const response = await fetch(`${API_BASE}/api/postiz/auth-url/${provider}?callback_url=${callbackUrl}`);
      const data = await response.json();
      
      if (data.url) {
        // 2. Open OAuth in popup
        const width = 600;
        const height = 700;
        const left = window.screen.width / 2 - width / 2;
        const top = window.screen.height / 2 - height / 2;
        
        const popup = window.open(
          data.url,
          'Connect Account',
          `width=${width},height=${height},left=${left},top=${top}`
        );
        
        // 3. Set up message listener for the popup
        const messageHandler = async (event: MessageEvent) => {
          if (event.origin !== window.location.origin) return;
          
          if (event.data?.type === 'POSTIZ_AUTH_COMPLETE') {
            const { code, state } = event.data;
            setConnectState(state);
            
            try {
              const connectResp = await fetch(`${API_BASE}/api/postiz/connect/${provider}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, state })
              });
              
              const connectData = await connectResp.json();
              if (connectData.success) {
                const result = connectData.data;
                
                // For Facebook/Instagram, they return pages that need to be selected
                if (result.pages && result.pages.length > 0) {
                  setPagesToConnect(result.pages);
                  setCurrentIntegrationId(result.id);
                  setConnecting(null);
                } else {
                  // Direct connection success (like Mastodon, X, etc.)
                  onAccountConnected();
                  onClose();
                }
              } else {
                setError(connectData.details || connectData.detail || 'Failed to finalize connection');
              }
            } catch (err) {
              setError('Error completing connection flow');
            } finally {
              if (!pagesToConnect) setConnecting(null);
              window.removeEventListener('message', messageHandler);
            }
          } else if (event.data?.type === 'POSTIZ_AUTH_ERROR') {
            setError(event.data.error || 'Authentication error');
            setConnecting(null);
            window.removeEventListener('message', messageHandler);
          }
        };
        
        window.addEventListener('message', messageHandler);
        
        const checkPopup = setInterval(() => {
          if (popup?.closed) {
            clearInterval(checkPopup);
            setTimeout(() => {
                setConnecting(curr => curr === provider ? null : curr);
                window.removeEventListener('message', messageHandler);
            }, 2000);
          }
        }, 1000);
        
      } else {
        setError(data.error || 'Failed to initiate connection. Please try again.');
        setConnecting(null);
      }
    } catch (error) {
      console.error('Failed to connect:', error);
      setError('Connection failed. Please check your network.');
      setConnecting(null);
    }
  };

  const handlePageSelect = async (pageId: string) => {
    if (!currentIntegrationId || !connectState) return;
    setConnecting('page-selection');
    
    try {
      const resp = await fetch(`${API_BASE}/api/postiz/connect/${currentIntegrationId}/page`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state: connectState,
          page: pageId
        })
      });
      
      const data = await resp.json();
      if (data.success) {
        onAccountConnected();
        onClose();
      } else {
        setError(data.details || data.detail || 'Failed to connect selected page');
      }
    } catch (err) {
      setError('Error finalizing page selection');
    } finally {
      setConnecting(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-gray-800">
            {pagesToConnect ? 'Select Facebook Page' : 'Connect Social Account'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 overflow-y-auto pr-2">
          {pagesToConnect ? (
            pagesToConnect.map(page => (
              <button
                key={page.id}
                onClick={() => handlePageSelect(page.id)}
                disabled={connecting === 'page-selection'}
                className="w-full flex items-center p-3 rounded-lg border-2 border-gray-100 hover:border-indigo-300 hover:bg-gray-50 transition-all"
              >
                <div className="w-10 h-10 rounded-full bg-gray-200 overflow-hidden flex-shrink-0">
                   {page.picture?.data?.url ? (
                     <img src={page.picture.data.url} alt={page.name} className="w-full h-full object-cover" />
                   ) : (
                     <div className="w-full h-full bg-blue-600 flex items-center justify-center text-white">
                       <Facebook className="w-5 h-5" />
                     </div>
                   )}
                </div>
                <div className="ml-3 text-left">
                  <span className="block font-medium text-gray-700 truncate">{page.name}</span>
                  <span className="block text-xs text-gray-500">@{page.username || page.id}</span>
                </div>
                {connecting === 'page-selection' && (
                  <span className="ml-auto flex h-2 w-2 rounded-full bg-indigo-600 animate-ping"></span>
                )}
              </button>
            ))
          ) : (
            platforms.map(platform => {
              const Icon = platform.icon;
              return (
                <button
                  key={platform.id}
                  onClick={() => handleConnect(platform.id)}
                  disabled={connecting !== null}
                  className={`w-full flex items-center p-3 rounded-lg border-2 transition-all 
                    ${connecting === platform.id 
                      ? 'border-indigo-500 bg-indigo-50' 
                      : 'border-gray-100 hover:border-indigo-300 hover:bg-gray-50'}
                    ${connecting !== null && connecting !== platform.id ? 'opacity-50 cursor-not-allowed' : ''}
                  `}
                >
                  <div className={`w-8 h-8 rounded-full ${platform.color} flex items-center justify-center text-white shadow-sm flex-shrink-0`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="ml-3 font-medium text-gray-700 truncate">{platform.name}</span>
                  {connecting === platform.id && (
                    <span className="ml-auto flex h-2 w-2 rounded-full bg-indigo-600 animate-ping"></span>
                  )}
                </button>
              );
            })
          )}
        </div>
        
        <div className="mt-6 pt-4 border-t flex justify-between items-center text-xs text-gray-500">
          {pagesToConnect ? (
            <button 
              onClick={() => setPagesToConnect(null)} 
              className="text-indigo-600 font-medium hover:underline"
            >
              ← Back to Platforms
            </button>
          ) : (
            <>
              <p>Redirects to Postiz for secure authentication.</p>
              <p>Direct flow enabled.</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConnectAccountModal;
