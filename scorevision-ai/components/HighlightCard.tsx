
import React, { useState } from 'react';
import { Highlight } from '../types.ts';

interface HighlightCardProps {
  highlight: Highlight;
  isActive: boolean;
  isSaved?: boolean;
  onSave?: () => void;
  onRemove?: () => void;
  onClick: () => void;
  sourceInfo?: string;
}

const HighlightCard: React.FC<HighlightCardProps> = ({ 
  highlight, 
  isActive, 
  isSaved = false, 
  onSave, 
  onRemove,
  onClick,
  sourceInfo 
}) => {
  const [saving, setSaving] = useState(false);

  const intensityColors = {
    High: 'bg-rose-500',
    Medium: 'bg-orange-500',
    Low: 'bg-amber-500'
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (highlight.clipUrl) {
      // Fix: Cast window to any to access document, satisfying environment checks where standard types might be incomplete
      const a = (window as any).document.createElement('a');
      a.href = highlight.clipUrl;
      a.download = `clip_${highlight.displayTime.replace(':', '-')}_${highlight.scoreType}.mp4`;
      (window as any).document.body.appendChild(a);
      a.click();
      (window as any).document.body.removeChild(a);
    }
  };

  const handleSaveAction = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isSaved) {
      onRemove?.();
    } else {
      setSaving(true);
      await onSave?.();
      setSaving(false);
    }
  };

  return (
    <div 
      onClick={onClick}
      className={`group p-4 rounded-xl cursor-pointer transition-all border ${
        isActive 
          ? 'bg-indigo-900/40 border-indigo-500 shadow-lg shadow-indigo-500/10 scale-[1.02]' 
          : 'bg-slate-800/50 border-slate-700 hover:border-slate-500'
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex flex-col">
          <span className="text-indigo-400 font-mono font-bold text-lg">{highlight.displayTime}</span>
          {sourceInfo && <span className="text-[10px] text-slate-500 uppercase tracking-tighter">{sourceInfo}</span>}
        </div>
        <div className="flex gap-2">
           <button 
            onClick={handleSaveAction}
            disabled={saving}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
              isSaved ? 'bg-rose-500 text-white' : 'bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-white'
            }`}
            title={isSaved ? "Remove from Gallery" : "Save to Gallery"}
          >
            <i className={`fas ${saving ? 'fa-circle-notch animate-spin' : isSaved ? 'fa-heart' : 'fa-heart-circle-plus'}`}></i>
          </button>
        </div>
      </div>
      
      <div className="flex justify-between items-center mb-2">
         <h4 className="text-slate-200 font-semibold">{highlight.scoreType}</h4>
         <div className="flex gap-1">
          <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded text-white ${intensityColors[highlight.intensity as keyof typeof intensityColors] || 'bg-slate-500'}`}>
            {highlight.intensity}
          </span>
          {highlight.playerJerseyNumber && highlight.playerJerseyNumber !== "Unknown" && (
            <span className="px-2 py-0.5 text-[10px] font-bold bg-indigo-600 rounded text-white border border-indigo-400/30">
              #{highlight.playerJerseyNumber}
            </span>
          )}
        </div>
      </div>
      
      <p className="text-slate-400 text-sm line-clamp-2 leading-relaxed mb-3">{highlight.description}</p>
      
      {highlight.clipUrl && (
        <div className="space-y-2">
          <video 
            src={highlight.clipUrl} 
            className="w-full rounded-lg bg-black border border-slate-700 aspect-video" 
            controlsList="nodownload"
            onMouseEnter={(e) => (e.target as any).play()}
            onMouseLeave={(e) => {
              const v = e.target as any;
              v.pause();
              v.currentTime = 0;
            }}
            muted
          />
          <button 
            onClick={handleDownload}
            className="w-full py-2 bg-slate-700 hover:bg-indigo-600 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2"
          >
            <i className="fas fa-download"></i>
            Download
          </button>
        </div>
      )}
    </div>
  );
};

export default HighlightCard;
