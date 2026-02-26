import React, { useState, useEffect } from 'react';
import { Clock, Film, Pencil, Download, Loader2, AlertCircle, Trash2 } from 'lucide-react';
import { ProjectStatus } from '../types';

interface ProjectHistoryItem extends ProjectStatus {
  id: string;
  title: string;
  created_at: string;
  is_legacy?: boolean;
}

interface ProjectHistoryStepProps {
  API_BASE: string;
  onEdit: (projectId: string) => void;
  onNew: () => void;
}

const ProjectHistoryStep: React.FC<ProjectHistoryStepProps> = ({ API_BASE, onEdit, onNew }) => {
  const [history, setHistory] = useState<ProjectHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/projects`);
      const data = await response.json();
      if (data.success) {
        setHistory(data.data);
      } else {
        throw new Error(data.error || 'Failed to fetch history');
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleDelete = async (projectId: string) => {
    if (!window.confirm('Are you sure you want to delete this project? This will also remove the video file from the server.')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/projects/${projectId}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      
      if (data.success) {
        // Update local state by filtering out the deleted project
        setHistory(prev => prev.filter(p => p.id !== projectId));
      } else {
        alert(`Failed to delete project: ${data.error || data.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Delete error:', err);
      alert(`Error deleting project: ${(err as Error).message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-20">
        <Loader2 className="w-12 h-12 text-primary animate-spin mb-4" />
        <p className="text-gray-500 font-medium">Loading your video history...</p>
      </div>
    );
  }

  return (
    <div className="card-custom">
      <div className="card-header-custom flex justify-between items-center">
        <h4 className="mb-0 text-xl font-semibold flex items-center">
          <Clock className="mr-2" /> Recent Projects
        </h4>
        <button className="btn-primary-custom px-4 py-2 text-sm" onClick={onNew}>
           Create New Video
        </button>
      </div>
      <div className="card-body p-0">
        {error ? (
          <div className="p-10 text-center">
             <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
             <p className="text-red-500">{error}</p>
             <button className="mt-4 text-primary font-bold" onClick={fetchHistory}>Retry</button>
          </div>
        ) : history.length === 0 ? (
          <div className="p-20 text-center text-gray-400">
             <Film className="w-12 h-12 mx-auto mb-4 opacity-20" />
             <p>No projects found. Create your first video!</p>
             <button className="btn-primary-custom mt-6" onClick={onNew}>Start Creating</button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50 text-gray-500 uppercase text-[0.7rem] font-bold tracking-wider">
                <tr>
                  <th className="px-6 py-4">Video Title</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Created At</th>
                  <th className="px-6 py-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map((project) => (
                  <tr key={project.id} className="hover:bg-gray-50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-bold text-gray-800">{project.title}</div>
                      <div className="text-[0.65rem] text-gray-400 font-mono">{project.id.split('-')[0]}...</div>
                    </td>
                    <td className="px-6 py-4">
                       <span className={`px-2 py-1 rounded-full text-[0.65rem] font-bold uppercase ${
                         project.status === 'completed' ? 'bg-green-100 text-green-600' : 
                         project.status === 'failed' ? 'bg-red-100 text-red-600' : 
                         'bg-blue-100 text-blue-600'
                       }`}>
                         {project.status}
                       </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDate(project.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex justify-center gap-2">
                         {!project.is_legacy && (
                           <button 
                             onClick={() => onEdit(project.id)}
                             className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors"
                             title="Re-edit Project"
                           >
                             <Pencil className="w-4 h-4" />
                           </button>
                         )}
                         {project.video_url && (
                           <a 
                             href={`${API_BASE}/api/download/${project.video_url.split('?')[0].split('/').pop()}`} 
                             target="_blank" 
                             rel="noopener noreferrer"
                             className="p-2 text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
                             title="Download Video"
                           >
                             <Download className="w-4 h-4" />
                           </a>
                         )}
                         <button 
                           onClick={() => handleDelete(project.id)}
                           className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                           title="Delete Project"
                         >
                           <Trash2 className="w-4 h-4" />
                         </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectHistoryStep;
