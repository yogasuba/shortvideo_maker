// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  detail?: string;
}

export interface ProjectStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: {
    message: string;
  } | string;
  video_url?: string;
}

export interface ConfigData {
  languages?: string[];
  voices?: Array<{
    id: string;
    name: string;
    language: string;
  }>;
  image_styles?: Array<{
    id: string;
    name: string;
    description: string;
  }>;
}

export interface SceneData {
  scene_number: number;
  description: string;
  voiceover: string;
}

export interface ScenesPreview {
  scenes: SceneData[];
}

export interface Interaction {
  id: string;
  name: string;
  picture?: string;
}

export interface PostizIntegration {
  id: string;
  name: string;
  platform: string;
  enabled: boolean;
  picture?: string;
  identifier?: string;
  disabled?: boolean;
}

export interface ScheduledPost {
  id: string;
  video_id: string;
  caption: string;
  platforms: string[];
  schedule_time: string;
  status: 'pending' | 'scheduled' | 'posted' | 'failed' | 'retrying';
  postiz_post_id?: string;
  error_message?: string;
  // New Backend Fields
  postiz_status?: string;
  error_source?: string;
  last_error_message?: string;
  // Legacy fields (optional)
  integration_id?: string;
  integration_name?: string;
  fb_permalink?: string;
}

// Component Prop Types
export type AlertType = 'success' | 'error' | 'info' | 'warning';

export interface Alert {
  id: number;
  message: string;
  type: AlertType;
}

export type ViewType = 'creator' | 'calendar' | 'integrations';
export type OrientationType = 'portrait' | 'landscape';
export type SubtitleStyleType = 'static' | 'scroll_up';
export type ToneType = 'neutral' | 'professional' | 'casual' | 'humorous' | 'educational' | 'motivational';

// Custom Hook Types
export type UsePersistentStateReturn<T> = [T, React.Dispatch<React.SetStateAction<T>>];
