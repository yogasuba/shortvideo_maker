import React, { useEffect } from 'react';

const PostizCallback: React.FC = () => {
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    let provider = urlParams.get('platform') || urlParams.get('provider'); // Postiz might use platform or provider
    
    // Extract provider from path if not in query params (for headless redirect)
    if (!provider && window.location.pathname.startsWith('/integrations/social/')) {
      provider = window.location.pathname.split('/').pop() || null;
    }

    if (window.opener) {
      if (code && state) {
        window.opener.postMessage(
          { 
            type: 'POSTIZ_AUTH_COMPLETE', 
            code, 
            state, 
            provider 
          }, 
          window.location.origin
        );
      } else {
        window.opener.postMessage(
          { 
            type: 'POSTIZ_AUTH_ERROR', 
            error: 'Missing code or state' 
          }, 
          window.location.origin
        );
      }
      
      // Auto close after a short delay to ensure message is sent
      setTimeout(() => {
        window.close();
      }, 1000);
    }
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white">
      <div className="p-8 rounded-xl shadow-lg border border-gray-100 text-center max-w-sm">
        <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">Connecting Account...</h2>
        <p className="text-gray-600">Please wait while we finalize the connection. This window will close automatically.</p>
      </div>
    </div>
  );
};

export default PostizCallback;
