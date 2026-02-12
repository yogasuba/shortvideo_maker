import React, { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight, 
  Clock, 
  Facebook, 
  ExternalLink,
  AlertCircle,
  X
} from 'lucide-react';
import { ScheduledPost, ViewType, ApiResponse } from '../types';

interface CalendarViewProps {
  API_BASE: string;
  setView: (view: ViewType) => void;
}

const CalendarView: React.FC<CalendarViewProps> = ({ API_BASE, setView }) => {
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedPost, setSelectedPost] = useState<ScheduledPost | null>(null);

  useEffect(() => {
    fetchScheduledPosts();
  }, []);

  const fetchScheduledPosts = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/facebook/scheduled-posts`);
      const data: ApiResponse<ScheduledPost[]> = await response.json();
      if (data.success && data.data) {
        setPosts(data.data);
      }
    } catch (error) {
      console.error('Error fetching calendar posts:', error);
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
                <Facebook size={10} className="mr-1" />
                <span className="truncate text-[10px]">{post.integration_name}</span>
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
                <Facebook className="text-blue-600 mr-2" size={18} />
                Post Details
              </h5>
              <button onClick={() => setSelectedPost(null)} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6">
              <div className="flex items-center gap-3 mb-6">
                {selectedPost.integration_picture ? (
                  <img src={selectedPost.integration_picture} className="w-12 h-12 rounded-full border-2 border-blue-50" />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                    {selectedPost.integration_name[0]}
                  </div>
                )}
                <div>
                  <h6 className="font-bold text-lg mb-0">{selectedPost.integration_name}</h6>
                  <p className="text-xs text-gray-500 flex items-center">
                    <Clock size={12} className="mr-1" /> 
                    {new Date(selectedPost.schedule_time).toLocaleString()}
                  </p>
                </div>
                <div className={`ml-auto px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider status-badge-${selectedPost.status}`}>
                  {selectedPost.status}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-900/30 p-4 rounded-xl mb-6 border dark:border-gray-700">
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {selectedPost.caption}
                </p>
              </div>

              {selectedPost.status === 'failed' && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 text-xs flex items-start mb-6 border border-red-100 dark:border-red-800">
                  <AlertCircle size={14} className="mr-2 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-bold">Error:</span> {selectedPost.error_message}
                  </div>
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
                  View on Facebook
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
      {/* Note: In React TSX with strict mode, we typically move generic styles to CSS files or stick to Tailwind. 
          The previous version had a <style jsx> block. I will preserve it but it might need 'styled-jsx' types or be moved to index.css.
          For this migration, I'll convert it to a standard style tag or move logic if needed. 
          Given this is likely Vite + Tailwind, raw style tags in render work but are not ideal. 
          I will keep it for parity but ideally should refactor later. */}
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
