import React from 'react';

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  detail?: string;
}

export interface ProjectStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  status_message?: string;
  error?: {
    message: string;
  } | string;
  video_url?: string;
}

export type Integration = PostizIntegration;

export interface ConfigData {
  languages?: string[];
  voices?: Array<{
    id: string;
    name: string;
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
  // Optional and extended fields
  text?: string;
  voice_over?: string;
  visual_prompt?: string;
  duration: number;
  duration_is_auto?: boolean;
  custom_audio_url?: string;
  custom_audio_path?: string;
  is_default?: boolean;
  is_system_default?: boolean;
  custom_image_url?: string;
  custom_image_path?: string;
  rotation?: number;
  subtitle_position?: 'bottom' | 'center';
  subtitle_size?: number;
  subtitle_bg_visible?: boolean;
  subtitle_color?: string;
  subtitle_bold?: boolean;
  show_image_only?: boolean;
  line_styles?: Array<Record<string, any>>;
}

export interface ScenesPreview {
  scenes: SceneData[];
  total_scenes?: number;
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
