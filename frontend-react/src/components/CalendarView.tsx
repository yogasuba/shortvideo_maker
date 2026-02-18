import React, { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight, 
  Clock, 
  Share2, 
  ExternalLink,
  AlertCircle,
  X
} from 'lucide-react';
import { ScheduledPost, ViewType, ApiResponse, PostizIntegration } from '../types';

interface CalendarViewProps {
  API_BASE: string;
  setView: (view: ViewType) => void;
}

const CalendarView: React.FC<CalendarViewProps> = ({ API_BASE, setView }) => {
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [integrations, setIntegrations] = useState<Record<string, PostizIntegration>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedPost, setSelectedPost] = useState<ScheduledPost | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch Posts
      const postsResp = await fetch(`${API_BASE}/api/scheduled-posts`);
      const postsData: ApiResponse<ScheduledPost[]> = await postsResp.json();
      
      // Fetch Integrations for mapping
      const intsResp = await fetch(`${API_BASE}/api/postiz/integrations`);
      const intsData: ApiResponse<PostizIntegration[]> = await intsResp.json();

      if (intsData.success && intsData.data) {
        const intMap: Record<string, PostizIntegration> = {};
        intsData.data.forEach(i => intMap[i.id] = i);
        setIntegrations(intMap);
      }

      if (postsData.success && postsData.data) {
        setPosts(postsData.data);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calendar Logic
  const daysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate();
  const firstDayOfMonth = (year: number, month: number) => new Date(year, month, 1).getDay();

  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const monthName = currentDate.toLocaleString('default', { month: 'long' });
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const getPlatformNames = (platformIds: string[]) => {
    if (!platformIds || platformIds.length === 0) return 'No platforms';
    return platformIds.map(id => integrations[id]?.name || 'Unknown').join(', ');
  };

  const renderDays = () => {
    const totalDays = daysInMonth(year, month);
    const firstDay = firstDayOfMonth(year, month);
    const dayCells: React.JSX.Element[] = [];

    // Empty cells for first week
    for (let i = 0; i < firstDay; i++) {
      dayCells.push(<div key={`empty-${i}`} className="calendar-day empty"></div>);
    }

    // Days of month
    for (let d = 1; d <= totalDays; d++) {
      const dayPosts = posts.filter(p => {
        if (!p.schedule_time) return false;
        const postDate = new Date(p.schedule_time);
        return postDate.getFullYear() === year && 
               postDate.getMonth() === month && 
               postDate.getDate() === d;
      });
      const isToday = new Date().toDateString() === new Date(year, month, d).toDateString();

      dayCells.push(
        <div key={d} className={`calendar-day ${isToday ? 'today' : ''}`}>
          <span className="day-number">{d}</span>
          <div className="day-posts">
            {dayPosts.map(post => (
              <div 
                key={post.id} 
                className={`post-pill status-${post.status}`}
                onClick={() => setSelectedPost(post)}
              >
                <Share2 size={10} className="mr-1" />
                <span className="truncate text-[10px]">
                  {post.platforms?.length > 1 
                    ? `${post.platforms.length} Platforms` 
                    : (integrations[post.platforms?.[0]]?.name || 'Post')}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    return dayCells;
  };

  return (
    <div className="calendar-container animate-fade-in">
      <div className="card-custom">
        <div className="card-header-custom flex justify-between items-center">
          <div className="flex items-center">
            <CalendarIcon className="mr-2 text-primary" />
            <h4 className="mb-0 text-xl font-bold">Content Calendar</h4>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex gap-1">
              <button onClick={prevMonth} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors">
                <ChevronLeft size={20} />
              </button>
              <button onClick={nextMonth} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors">
                <ChevronRight size={20} />
              </button>
            </div>
            <h5 className="mb-0 font-semibold min-w-[120px] text-center">{monthName} {year}</h5>
            <button 
              onClick={() => setView('creator')} 
              className="ml-2 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 hover:text-red-700 dark:text-red-500 dark:hover:text-red-400 rounded-full transition-colors"
              title="Close Calendar"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        <div className="card-body p-0 border-t border-gray-200 dark:border-gray-700">
          <div className="calendar-grid">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
              <div key={day} className="calendar-header-day">{day}</div>
            ))}
            {loading ? (
              <div className="col-span-7 h-64 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : renderDays()}
          </div>
        </div>
      </div>

      {/* Post Detail Modal */}
      {selectedPost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-scale-up">
            <div className="p-4 border-b dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900/50">
              <h5 className="font-bold flex items-center">
                <Share2 className="text-blue-600 mr-2" size={18} />
                Post Details
              </h5>
              <button onClick={() => setSelectedPost(null)} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6">
              <div className="flex flex-col gap-1 mb-6">
                <h6 className="font-bold text-lg mb-0">Scheduled for {getPlatformNames(selectedPost.platforms)}</h6>
                <p className="text-xs text-gray-500 flex items-center">
                  <Clock size={12} className="mr-1" /> 
                  {new Date(selectedPost.schedule_time).toLocaleString()}
                </p>
                <div className="flex gap-2 mt-2">
                   <div className={`w-fit px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider status-badge-${selectedPost.status}`}>
                    {selectedPost.status}
                  </div>
                  {selectedPost.postiz_status && selectedPost.postiz_status !== 'SCHEDULED' && selectedPost.postiz_status !== 'COMPLETED' && (
                     <div className="w-fit px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                        {selectedPost.postiz_status}
                     </div>
                  )}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-900/30 p-4 rounded-xl mb-6 border dark:border-gray-700">
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {selectedPost.caption}
                </p>
              </div>

              {(selectedPost.status === 'failed' || selectedPost.last_error_message) && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 text-xs flex flex-col gap-1 mb-6 border border-red-100 dark:border-red-800">
                  <div className="flex items-start">
                      <AlertCircle size={14} className="mr-2 mt-0.5 shrink-0" />
                      <div>
                        <span className="font-bold">Error:</span> {selectedPost.error_message || selectedPost.last_error_message || "Unknown Error"}
                      </div>
                  </div>
                  {selectedPost.error_source && (
                      <div className="ml-6 text-[10px] opacity-75">
                          Source: {selectedPost.error_source}
                      </div>
                  )}
                </div>
              )}

              {selectedPost.fb_permalink && (
                <a 
                  href={selectedPost.fb_permalink} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center gap-2 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold transition-all mb-4"
                >
                  <ExternalLink size={18} />
                  View Post
                </a>
              )}

              <button 
                onClick={() => setSelectedPost(null)}
                className="w-full p-3 border-2 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl font-semibold transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Styles */}
      <style>{`
        .calendar-grid {
          display: grid;
          grid-template-columns: repeat(7, 1fr);
        }
        .calendar-header-day {
          padding: 12px;
          text-align: center;
          font-weight: bold;
          font-size: 0.75rem;
          color: #6b7280;
          border-bottom: 1px solid #e5e7eb;
          text-transform: uppercase;
          background: #f9fafb;
        }
        .dark-theme .calendar-header-day {
          background: #111827;
          border-color: #374151;
          color: #9ca3af;
        }
        .calendar-day {
          min-height: 120px;
          padding: 10px;
          border-right: 1px solid #e5e7eb;
          border-bottom: 1px solid #e5e7eb;
          position: relative;
          transition: background 0.2s;
        }
        .dark-theme .calendar-day {
          border-color: #374151;
        }
        .calendar-day:nth-child(7n) {
          border-right: none;
        }
        .calendar-day.empty {
          background: #f9fafb;
        }
        .dark-theme .calendar-day.empty {
          background: #030712;
        }
        .calendar-day.today {
          background: #eff6ff;
        }
        .dark-theme .calendar-day.today {
          background: #1e3a8a30;
        }
        .day-number {
          font-weight: 600;
          font-size: 0.875rem;
          margin-bottom: 8px;
          display: block;
        }
        .today .day-number {
          color: #2563eb;
          font-weight: 800;
        }
        .day-posts {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .post-pill {
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 0.7rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          transition: transform 0.1s;
        }
        .post-pill:hover {
          transform: translateY(-1px);
          filter: brightness(0.95);
        }
        .status-scheduled {
          background: #dbeafe;
          color: #1e40af;
          border-left: 3px solid #3b82f6;
        }
        .dark-theme .status-scheduled {
          background: #1e3a8a;
          color: #bfdbfe;
        }
        .status-posted {
          background: #dcfce7;
          color: #166534;
          border-left: 3px solid #22c55e;
        }
        .dark-theme .status-posted {
          background: #064e3b;
          color: #d1fae5;
        }
        .status-failed {
          background: #fee2e2;
          color: #991b1b;
          border-left: 3px solid #ef4444;
        }
        .dark-theme .status-failed {
          background: #7f1d1d;
          color: #fecaca;
        }
        .status-badge-scheduled { background: #3b82f6; color: white; }
        .status-badge-posted { background: #22c55e; color: white; }
        .status-badge-failed { background: #ef4444; color: white; }
        
        @keyframes scale-up {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-scale-up {
          animation: scale-up 0.2s ease-out forwards;
        }
      `}</style>
    </div>
  );
};

export default CalendarView;
