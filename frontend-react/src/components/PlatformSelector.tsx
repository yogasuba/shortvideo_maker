import React from 'react';
import { Check, Plus, Loader2 } from 'lucide-react';
import { PostizIntegration } from '../types';

interface PlatformSelectorProps {
  platforms: PostizIntegration[];
  selected: string[];
  onChange: (selected: string[]) => void;
  isLoading?: boolean;
  onConnect?: () => void;
  API_BASE: string;
}

const PlatformSelector: React.FC<PlatformSelectorProps> = ({ 
  platforms, selected, onChange, onConnect, isLoading = false, API_BASE 
}) => {
  
  const togglePlatform = (id: string) => {
    if (selected.includes(id)) {
      onChange(selected.filter(p => p !== id));
    } else {
      onChange([...selected, id]);
    }
  };

  const getPlatformIcon = (platform: string) => {
    const colorMap: Record<string, string> = {
      facebook: 'bg-blue-600',
      instagram: 'bg-pink-600',
      tiktok: 'bg-black',
      youtube: 'bg-red-600',
      twitter: 'bg-black',
      linkedin: 'bg-blue-700',
      reddit: 'bg-orange-600',
      pinterest: 'bg-red-700',
      discord: 'bg-indigo-600',
      slack: 'bg-purple-600',
      threads: 'bg-black',
      mastodon: 'bg-indigo-700',
      github: 'bg-gray-800',
      dribbble: 'bg-pink-500',
      beehiive: 'bg-yellow-500',
    };
    
    const initial = platform.charAt(0).toUpperCase();
    const bgColor = colorMap[platform.toLowerCase()] || 'bg-gray-500';
    
    return (
      <div className={`w-8 h-8 rounded-full ${bgColor} flex items-center justify-center text-white font-bold text-xs ring-2 ring-white/10`}>
        {initial}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (platforms.length === 0) {
    return (
      <div className="text-center p-6 border-2 border-dashed border-gray-200 rounded-lg">
        <p className="text-gray-500 mb-4">No social accounts connected yet.</p>
        <button 
          onClick={onConnect}
          className="btn-primary-custom inline-flex items-center"
        >
          <Plus className="w-4 h-4 mr-2" /> Connect Accounts
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {platforms.map(platform => {
          const isSelected = selected.includes(platform.id);
          const isEnabled = platform.enabled !== undefined ? platform.enabled : !platform.disabled;
          const isDisabled = !isEnabled;
          
          // Use platform string as primary name, handle 'unknown' gracefully
          const platformType = platform.platform.toLowerCase();
          const displayType = platformType === 'unknown' ? 'Unknown' : 
            platformType.charAt(0).toUpperCase() + platformType.slice(1);
          
          return (
            <div
              key={platform.id}
              onClick={() => !isDisabled && togglePlatform(platform.id)}
              className={`
                relative p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center group
                ${isSelected 
                  ? 'border-indigo-500 bg-indigo-50 shadow-sm' 
                  : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50 shadow-sm'}
                ${isDisabled ? 'opacity-50 cursor-not-allowed grayscale' : ''}
              `}
            >
              {getPlatformIcon(platformType === 'unknown' ? platform.identifier || '?' : platformType)}
              <div className="ml-3 overflow-hidden">
                <h5 className="font-bold text-sm text-gray-800 truncate leading-tight" title={platform.name}>
                  {platform.name}
                </h5>
                <p className="text-[10px] font-bold uppercase tracking-wider mt-0.5" 
                   style={{color: platformType === 'unknown' ? '#ef4444' : '#6366f1'}}>
                  {displayType}
                </p>
              </div>
              
              {isSelected && (
                <div className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-white shadow-sm">
                  <Check className="w-3 h-3" />
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-100 text-center">
        <button 
          onClick={onConnect}
          className="inline-flex items-center px-4 py-2 bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition-colors font-semibold text-sm"
        >
          <Plus className="w-4 h-4 mr-2" />
          Connect More Accounts
        </button>
      </div>
    </>
  );
};

export default PlatformSelector;
