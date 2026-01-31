
import React, { useState, useRef, useEffect, useMemo } from 'react';
import { analyzeVideo } from './services/geminiService.ts';
import { Highlight, AnalysisStatus, AnalysisResult, HistoryItem, GalleryItem } from './types.ts';
import { getGallery, saveToGallery, removeFromGallery } from './services/db.ts';
import { checkClipServerHealth, generateClipsViaAPI, ClipResponse } from './services/clipService.ts';
import * as backendApi from './services/backendApi.ts';
import Timeline from './components/Timeline.tsx';
import HighlightCard from './components/HighlightCard.tsx';
import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';

const CACHE_KEY = 'scorevision_history_v1';

interface CloudClip {
  url: string;
  signedUrl: string;
  start: number;
  end: number;
  index: number;
}

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'analysis' | 'gallery'>('analysis');
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>(AnalysisStatus.IDLE);
  const [results, setResults] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [gallery, setGallery] = useState<GalleryItem[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [clippingProgress, setClippingProgress] = useState(0);
  const [targetJersey, setTargetJersey] = useState<string>('');
  const [hasKey, setHasKey] = useState(false);
  const [engineReady, setEngineReady] = useState<boolean | null>(null);
  const [clipServerReady, setClipServerReady] = useState<boolean | null>(null);
  const [videoPathInput, setVideoPathInput] = useState<string>('');
  const [serverClipResult, setServerClipResult] = useState<ClipResponse | null>(null);
  const [serverClipping, setServerClipping] = useState(false);

  const [cloudMode, setCloudMode] = useState(true);
  const [backendReady, setBackendReady] = useState<boolean | null>(null);
  const [cloudVideoId, setCloudVideoId] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [cloudClips, setCloudClips] = useState<CloudClip[]>([]);
  const [cloudReelUrl, setCloudReelUrl] = useState<string | null>(null);

  const videoRef = useRef<any>(null);
  const ffmpegRef = useRef<FFmpeg | null>(null);

  useEffect(() => {
    const savedHistory = localStorage.getItem(CACHE_KEY);
    if (savedHistory) {
      try { setHistory(JSON.parse(savedHistory)); } catch (e) { console.error(e); }
    }

    const loadGalleryItems = async () => {
      try {
        const items = await getGallery();
        const itemsWithUrls = items.map(item => ({
          ...item,
          clipUrl: item.clipBlob ? URL.createObjectURL(item.clipBlob) : undefined
        }));
        setGallery(itemsWithUrls);
      } catch (e) { console.error("Gallery Load Error:", e); }
    };
    loadGalleryItems();

    const checkKey = async () => {
      if ((window as any).aistudio?.hasSelectedApiKey) {
        try {
          const selected = await (window as any).aistudio.hasSelectedApiKey();
          setHasKey(selected);
        } catch (e) { setHasKey(false); }
      } else { setHasKey(true); }
    };
    checkKey();

    const checkClipServer = async () => {
      const ready = await checkClipServerHealth();
      setClipServerReady(ready);
    };
    checkClipServer();
    const interval = setInterval(checkClipServer, 5000);

    const checkBackend = async () => {
      const ready = await backendApi.checkBackendHealth();
      setBackendReady(ready);
    };
    checkBackend();
    const backendInterval = setInterval(checkBackend, 5000);

    return () => {
      clearInterval(interval);
      clearInterval(backendInterval);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(CACHE_KEY, JSON.stringify(history));
  }, [history]);

  const getFileId = (file: File) => `${file.name}-${file.size}-${file.lastModified}`;

  const filteredHighlights = useMemo(() => {
    if (!results) return [];
    if (!targetJersey.trim()) return results.highlights;
    return results.highlights.filter(h => h.playerJerseyNumber?.toLowerCase().includes(targetJersey.trim().toLowerCase()));
  }, [results, targetJersey]);

  const filteredGallery = useMemo(() => {
    if (!targetJersey.trim()) return gallery;
    return gallery.filter(h => h.playerJerseyNumber?.toLowerCase().includes(targetJersey.trim().toLowerCase()));
  }, [gallery, targetJersey]);

  const loadFFmpeg = async () => {
    if (ffmpegRef.current) return ffmpegRef.current;
    
    const ffmpeg = new FFmpeg();
    const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm';
    
    try {
      ffmpeg.on('log', ({ message }) => console.debug(`[FFmpeg] ${message}`));

      await ffmpeg.load({
        coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
        wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
        workerURL: await toBlobURL(`${baseURL}/ffmpeg-core.worker.js`, 'text/javascript'),
      });
      ffmpegRef.current = ffmpeg;
      setEngineReady(true);
      return ffmpeg;
    } catch (err) {
      console.error("FFmpeg Load Error:", err);
      setEngineReady(false);
      throw new Error("Video engine blocked by browser security. Clips cannot be generated, but AI analysis will still work.");
    }
  };

  const generateClips = async (analysis: AnalysisResult, file: File) => {
    if (!analysis.highlights.length) return analysis;
    
    let ffmpeg: FFmpeg;
    try {
      ffmpeg = await loadFFmpeg();
    } catch (e) {
      console.warn("Skipping clipping phase: Engine not available.");
      return analysis;
    }

    setStatus(AnalysisStatus.CLIPPING);
    setClippingProgress(0);

    const isAudioOnly = file.type.startsWith('audio/') || file.name.endsWith('.mp3');
    const extension = file.name.split('.').pop() || 'mp4';
    const inputFileName = `input.${extension}`;

    try {
      await ffmpeg.writeFile(inputFileName, await fetchFile(file));
      const updatedHighlights = [...analysis.highlights];
      
      for (let i = 0; i < updatedHighlights.length; i++) {
        const h = updatedHighlights[i];
        const start = Math.max(0, h.timestampSeconds - 5);
        const clipDuration = 10;
        const outputName = `clip_${i}.${isAudioOnly ? extension : 'mp4'}`;
        
        try {
          // Use faster '-c copy' but fallback to encoding if it fails (common with bad seek points)
          await ffmpeg.exec(['-ss', start.toString(), '-i', inputFileName, '-t', clipDuration.toString(), '-c', 'copy', outputName]);
          const data = await ffmpeg.readFile(outputName);
          const mimeType = isAudioOnly ? file.type : 'video/mp4';
          const blob = new Blob([data], { type: mimeType });
          
          updatedHighlights[i] = { 
            ...h, 
            clipBlob: blob, 
            clipUrl: URL.createObjectURL(blob) 
          };
        } catch (clipErr) {
          console.warn(`Fast-cut failed for clip ${i}, trying slow-reencode...`);
          try {
             await ffmpeg.exec(['-ss', start.toString(), '-i', inputFileName, '-t', clipDuration.toString(), '-c:v', 'libx264', '-preset', 'ultrafast', outputName]);
             const data = await ffmpeg.readFile(outputName);
             const blob = new Blob([data], { type: 'video/mp4' });
             updatedHighlights[i] = { ...h, clipBlob: blob, clipUrl: URL.createObjectURL(blob) };
          } catch (e2) {
             console.error(`Clip ${i} failed entirely`, e2);
          }
        }
        setClippingProgress(Math.round(((i + 1) / updatedHighlights.length) * 100));
      }
      return { ...analysis, highlights: updatedHighlights };
    } catch (err: any) {
      console.error("FFmpeg Runtime Error:", err);
      return analysis;
    }
  };

  const startAnalysis = async () => {
    if (!videoFile) return;
    setError(null);
    
    if (cloudMode && backendReady) {
      await startCloudAnalysis();
      return;
    }
    
    const fileId = getFileId(videoFile);
    const cached = history.find(item => item.id === fileId);
    
    if (cached) {
      const restored = await generateClips(cached.result, videoFile);
      setResults(restored);
      setStatus(AnalysisStatus.COMPLETED);
      return;
    }

    try {
      setStatus(AnalysisStatus.UPLOADING);
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve) => {
        reader.onload = () => resolve((reader.result as string).split(',')[1]);
        reader.readAsDataURL(videoFile);
      });
      const base64 = await base64Promise;
      
      setStatus(AnalysisStatus.ANALYZING);
      let analysis = await analyzeVideo(base64, videoFile.type);
      
      const historyItem: HistoryItem = { 
        id: fileId, 
        fileName: videoFile.name, 
        timestamp: Date.now(), 
        result: analysis 
      };
      setHistory(prev => [historyItem, ...prev.filter(h => h.id !== fileId)].slice(0, 10));
      
      analysis = await generateClips(analysis, videoFile);
      setResults(analysis);
      setStatus(AnalysisStatus.COMPLETED);
    } catch (err: any) {
      console.error("StartAnalysis Error:", err);
      setError(err.message || 'Analysis failed.');
      setStatus(AnalysisStatus.ERROR);
    }
  };

  const startCloudAnalysis = async () => {
    if (!videoFile) return;
    
    try {
      setStatus(AnalysisStatus.UPLOADING);
      setUploadProgress(0);
      
      const uploadResult = await backendApi.uploadVideo(videoFile, (progress) => {
        setUploadProgress(progress);
      });
      
      setCloudVideoId(uploadResult.videoId);
      setVideoUrl(uploadResult.signedUrl);
      
      setStatus(AnalysisStatus.ANALYZING);
      
      const analysisResult = await backendApi.analyzeVideo(uploadResult.videoId);
      
      const analysisForState: AnalysisResult = {
        highlights: analysisResult.highlights.map(h => ({
          timestampSeconds: h.timestampSeconds,
          displayTime: h.displayTime,
          description: h.description,
          scoreType: h.scoreType,
          intensity: h.intensity as 'High' | 'Medium' | 'Low',
          playerJerseyNumber: h.playerJerseyNumber,
        })),
        summary: analysisResult.summary,
        videoId: analysisResult.videoId,
      };
      
      setResults(analysisForState);
      setStatus(AnalysisStatus.COMPLETED);
      
    } catch (err: any) {
      console.error("Cloud Analysis Error:", err);
      setError(err.message || 'Cloud analysis failed.');
      setStatus(AnalysisStatus.ERROR);
    }
  };

  const generateCloudClips = async () => {
    if (!cloudVideoId || !results) return;
    
    setServerClipping(true);
    setError(null);
    
    try {
      const clipsResult = await backendApi.generateClips(cloudVideoId, {
        preSeconds: 6,
        postSeconds: 4,
        makeReel: true,
      });
      
      setCloudClips(clipsResult.clips);
      setCloudReelUrl(clipsResult.reelSignedUrl);
      
      const updatedHighlights = results.highlights.map((h, i) => {
        const clip = clipsResult.clips.find(c => c.index === i);
        return {
          ...h,
          clipUrl: clip?.signedUrl,
        };
      });
      
      setResults({
        ...results,
        highlights: updatedHighlights,
      });
      
    } catch (err: any) {
      console.error("Cloud Clips Error:", err);
      setError(err.message || 'Cloud clip generation failed.');
    } finally {
      setServerClipping(false);
    }
  };

  const handleSaveToGallery = async (highlight: Highlight) => {
    if (!highlight.clipBlob) {
        // Allow saving metadata even if clip failed
        console.warn("Saving highlight without clip blob");
    }
    if (!videoFile) return;

    const id = `${getFileId(videoFile)}-${highlight.timestampSeconds}`;
    const galleryItem: GalleryItem = {
      ...highlight,
      id,
      sourceFileName: videoFile.name,
      savedAt: Date.now(),
    };

    try {
      await saveToGallery(galleryItem);
      const newItem = { ...galleryItem, clipUrl: highlight.clipUrl };
      setGallery(prev => [...prev.filter(i => i.id !== id), newItem]);
    } catch (e) { 
      console.error("Gallery Save Error:", e);
      setError("Storage error: Gallery items might be too large.");
    }
  };

  const handleRemoveFromGallery = async (id: string) => {
    try {
      await removeFromGallery(id);
      setGallery(prev => prev.filter(i => i.id !== id));
    } catch (e) { console.error("Gallery Remove Error:", e); }
  };

  const handleServerClip = async () => {
    if (!results || !videoPathInput.trim()) return;
    
    setServerClipping(true);
    setError(null);
    setServerClipResult(null);
    
    try {
      const result = await generateClipsViaAPI({
        videoPath: videoPathInput.trim(),
        analysis: results,
        outputDir: `outputs/${videoFile?.name.replace(/\.[^/.]+$/, '') || 'clips'}`,
        preSeconds: 6,
        postSeconds: 4,
        makeReel: true,
      });
      
      setServerClipResult(result);
    } catch (e: any) {
      setError(e.message || 'Server clipping failed');
    } finally {
      setServerClipping(false);
    }
  };

  const jumpToHighlight = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, seconds - 2);
      videoRef.current.play();
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) setDuration(videoRef.current.duration);
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
  };

  if (!hasKey) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center mb-6 shadow-2xl">
          <i className="fas fa-key text-white text-2xl"></i>
        </div>
        <h2 className="text-2xl font-bold mb-4">Gemini API Key Required</h2>
        <button onClick={async () => { await (window as any).aistudio.openSelectKey(); setHasKey(true); }} className="px-10 py-5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold transition-all shadow-xl">Select API Key</button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-200">
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20"><i className="fas fa-eye text-white text-xl"></i></div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">ScoreVision AI</h1>
            </div>
            <nav className="flex items-center gap-1 bg-slate-800/50 p-1 rounded-lg">
              <button onClick={() => setActiveTab('analysis')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'analysis' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>Analysis</button>
              <button onClick={() => setActiveTab('gallery')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'gallery' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>Gallery {gallery.length > 0 && <span className="bg-rose-500 text-white text-[10px] px-1.5 rounded-full min-w-[18px] text-center">{gallery.length}</span>}</button>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700">
              <span className="text-xs text-slate-400">Mode:</span>
              <button
                onClick={() => setCloudMode(false)}
                className={`px-2 py-0.5 text-xs rounded transition-all ${!cloudMode ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
              >
                Local
              </button>
              <button
                onClick={() => setCloudMode(true)}
                className={`px-2 py-0.5 text-xs rounded transition-all flex items-center gap-1 ${cloudMode ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
              >
                Cloud
                <span className={`w-1.5 h-1.5 rounded-full ${backendReady ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
              </button>
            </div>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i className="fas fa-search text-slate-500"></i></div>
              <input type="text" placeholder="Filter jersey #..." value={targetJersey} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTargetJersey(e.target.value)} className="bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-1.5 text-sm focus:ring-2 focus:ring-indigo-500 w-32 md:w-48 outline-none" />
            </div>
            {videoFile && activeTab === 'analysis' && results && (
              <button 
                onClick={() => {
                  const dataStr = JSON.stringify(results, null, 2);
                  const blob = new Blob([dataStr], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `analysis_${videoFile.name.replace(/\.[^/.]+$/, '')}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }} 
                className="text-sm font-medium text-emerald-400 hover:text-white bg-emerald-800/30 hover:bg-emerald-700/50 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
              >
                <i className="fas fa-download"></i>
                Export JSON
              </button>
            )}
            {videoFile && activeTab === 'analysis' && (
              <button onClick={() => { 
                setVideoFile(null); 
                setResults(null); 
                setStatus(AnalysisStatus.IDLE); 
                setVideoUrl(null); 
                setCloudVideoId(null);
                setCloudClips([]);
                setCloudReelUrl(null);
                setUploadProgress(0);
              }} className="text-sm font-medium text-slate-400 hover:text-white bg-slate-800/50 px-4 py-2 rounded-lg transition-colors">New File</button>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full p-4 lg:p-8">
        {activeTab === 'analysis' ? (
          !videoFile ? (
            <div className="h-[60vh] flex flex-col items-center justify-center text-center space-y-8">
              <h2 className="text-4xl font-extrabold text-white">AI Sports Hub</h2>
              <p className="text-slate-500 max-w-lg">Upload sports recordings to automatically detect highlights and identify players by jersey numbers.</p>
              <label className="group relative block w-full max-w-xl aspect-video rounded-3xl border-2 border-dashed border-slate-700 bg-slate-800/20 hover:border-indigo-500 transition-all cursor-pointer">
                <input type="file" accept="video/*,audio/*" onChange={(e: any) => { const file = e.target.files?.[0]; if (file) { setVideoFile(file); setVideoUrl(URL.createObjectURL(file)); setStatus(AnalysisStatus.IDLE); setResults(null); } }} className="hidden" />
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                  <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center shadow-xl group-hover:bg-indigo-600 transition-all"><i className="fas fa-clapperboard text-2xl text-slate-400 group-hover:text-white"></i></div>
                  <p className="text-xl font-semibold text-white">Upload Sports Recording</p>
                </div>
              </label>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div className="lg:col-span-8 space-y-6">
                <div className="relative aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl border border-slate-800">
                  {videoUrl && (
                    videoFile.type.startsWith('audio/') ? 
                    <audio ref={videoRef} src={videoUrl} onLoadedMetadata={handleLoadedMetadata} onTimeUpdate={handleTimeUpdate} className="w-full absolute bottom-4 px-8" controls /> : 
                    <video ref={videoRef} src={videoUrl} onLoadedMetadata={handleLoadedMetadata} onTimeUpdate={handleTimeUpdate} className="w-full h-full" controls />
                  )}
                  {(status !== AnalysisStatus.IDLE && status !== AnalysisStatus.COMPLETED && status !== AnalysisStatus.ERROR) && (
                    <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-md flex flex-col items-center justify-center z-20 text-center p-8">
                      <div className="w-24 h-24 mb-6 relative">
                        <div className="absolute inset-0 border-4 border-indigo-500/10 rounded-full animate-pulse"></div>
                        <div className="absolute inset-0 border-4 border-indigo-500 rounded-full border-t-transparent animate-spin"></div>
                        <i className={`fas ${status === AnalysisStatus.ANALYZING ? 'fa-brain' : status === AnalysisStatus.UPLOADING ? 'fa-cloud-arrow-up' : 'fa-scissors'} text-indigo-500 text-3xl absolute inset-0 flex items-center justify-center`}></i>
                      </div>
                      <h3 className="text-2xl font-bold mb-2 text-white">
                        {status === AnalysisStatus.UPLOADING && (cloudMode ? 'Uploading to Cloud...' : 'Reading Match...')}
                        {status === AnalysisStatus.ANALYZING && 'AI Analyzing Match...'}
                        {status === AnalysisStatus.CLIPPING && 'Creating Clips...'}
                      </h3>
                      {status === AnalysisStatus.UPLOADING && cloudMode && uploadProgress > 0 && (
                        <div className="mt-6 w-full max-w-xs">
                          <div className="bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div className="bg-indigo-500 h-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                          </div>
                          <p className="text-sm text-slate-400 mt-2">{uploadProgress}%</p>
                        </div>
                      )}
                      {status === AnalysisStatus.CLIPPING && (
                        <div className="mt-6 w-full max-w-xs bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div className="bg-indigo-500 h-full transition-all duration-300" style={{ width: `${clippingProgress}%` }}></div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {status === AnalysisStatus.COMPLETED && duration > 0 && (
                  <div className="bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
                    <Timeline duration={duration} currentTime={currentTime} highlights={filteredHighlights} onMarkerClick={jumpToHighlight} />
                  </div>
                )}
                {status === AnalysisStatus.IDLE && (
                  <div className="flex justify-center">
                    <button onClick={startAnalysis} className="px-10 py-5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold shadow-2xl transition-all transform hover:-translate-y-1">
                      Start AI Analysis
                    </button>
                  </div>
                )}
                {error && (
                  <div className="p-5 bg-rose-500/10 border border-rose-500/50 rounded-2xl text-rose-500 flex items-center gap-4 animate-shake">
                    <i className="fas fa-exclamation-circle"></i>
                    <span className="text-sm font-medium">{error}</span>
                  </div>
                )}
                {status === AnalysisStatus.COMPLETED && (
                  <div className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl space-y-3">
                    {cloudMode && cloudVideoId ? (
                      <>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${backendReady ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                            <span className="text-sm text-slate-400">
                              Cloud Backend: {backendReady ? 'Connected' : 'Not available'}
                            </span>
                          </div>
                          <span className="text-xs text-slate-500">Video ID: {cloudVideoId}</span>
                        </div>
                        
                        {cloudClips.length === 0 ? (
                          <button
                            onClick={generateCloudClips}
                            disabled={serverClipping || !backendReady}
                            className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg font-medium transition-all flex items-center justify-center gap-2"
                          >
                            {serverClipping ? (
                              <>
                                <i className="fas fa-spinner animate-spin"></i>
                                Generating Clips in Cloud...
                              </>
                            ) : (
                              <>
                                <i className="fas fa-cloud-arrow-up"></i>
                                Generate Clips (Cloud FFmpeg)
                              </>
                            )}
                          </button>
                        ) : (
                          <div className="space-y-4">
                            <div className="p-3 bg-emerald-500/10 border border-emerald-500/50 rounded-lg text-emerald-400 text-sm flex items-center justify-between">
                              <p className="font-medium">Generated {cloudClips.length} clips in the cloud!</p>
                              {cloudReelUrl && (
                                <a
                                  href={cloudReelUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-2 text-xs bg-indigo-600 text-white px-3 py-1.5 rounded-lg hover:bg-indigo-500 transition-all"
                                >
                                  <i className="fas fa-film"></i>
                                  Watch Full Reel
                                </a>
                              )}
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              {cloudClips.map((clip, index) => (
                                <div key={clip.index} className="bg-slate-900 rounded-lg overflow-hidden border border-slate-700">
                                  <video 
                                    src={clip.signedUrl} 
                                    className="w-full aspect-video bg-black" 
                                    controls
                                    preload="metadata"
                                  />
                                  <div className="p-2 flex items-center justify-between">
                                    <span className="text-xs text-slate-400">Clip {index + 1}</span>
                                    <a
                                      href={clip.signedUrl}
                                      download={`clip_${index + 1}.mp4`}
                                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                                    >
                                      <i className="fas fa-download"></i>
                                      Download
                                    </a>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${clipServerReady ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                            <span className="text-sm text-slate-400">
                              Local Clip Server: {clipServerReady ? 'Connected' : 'Not running'}
                            </span>
                          </div>
                          {!clipServerReady && (
                            <code className="text-xs bg-slate-900 px-2 py-1 rounded text-slate-500">
                              python server.py
                            </code>
                          )}
                        </div>
                        
                        {clipServerReady && (
                          <div className="space-y-2">
                            <input
                              type="text"
                              placeholder="Enter full video path (e.g., /Users/you/video.mp4)"
                              value={videoPathInput}
                              onChange={(e) => setVideoPathInput(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                            />
                            <button
                              onClick={handleServerClip}
                              disabled={!videoPathInput.trim() || serverClipping}
                              className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg font-medium transition-all flex items-center justify-center gap-2"
                            >
                              {serverClipping ? (
                                <>
                                  <i className="fas fa-spinner animate-spin"></i>
                                  Generating Clips...
                                </>
                              ) : (
                                <>
                                  <i className="fas fa-scissors"></i>
                                  Generate Clips (Local FFmpeg)
                                </>
                              )}
                            </button>
                          </div>
                        )}
                        
                        {serverClipResult && (
                          <div className="p-3 bg-emerald-500/10 border border-emerald-500/50 rounded-lg text-emerald-400 text-sm">
                            <p className="font-medium">Generated {serverClipResult.numClips} clips!</p>
                            <p className="text-xs text-slate-400 mt-1">
                              Saved to: {serverClipResult.outputDir}/
                              {serverClipResult.reel && <span className="block">Reel: {serverClipResult.reel}</span>}
                            </p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
              <div className="lg:col-span-4 flex flex-col">
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl flex flex-col h-[calc(100vh-12rem)] shadow-2xl overflow-hidden sticky top-24">
                  <div className="p-6 border-b border-slate-800 bg-slate-800/20 flex items-center justify-between">
                    <h3 className="font-bold text-lg text-white">Match Log</h3>
                    <span className="bg-indigo-600 text-white px-3 py-1 rounded-full text-xs font-bold">{filteredHighlights.length} Events</span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                    {status === AnalysisStatus.COMPLETED ? (
                      filteredHighlights.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-500 italic text-center p-8">
                          No events found.
                        </div>
                      ) : (
                        filteredHighlights.map((h, i) => (
                          <HighlightCard 
                            key={i} highlight={h} 
                            isActive={Math.abs(currentTime - h.timestampSeconds) < 2.0} 
                            isSaved={gallery.some(g => g.id === `${getFileId(videoFile!)}-${h.timestampSeconds}`)}
                            onSave={() => handleSaveToGallery(h)}
                            onRemove={() => handleRemoveFromGallery(`${getFileId(videoFile!)}-${h.timestampSeconds}`)}
                            onClick={() => jumpToHighlight(h.timestampSeconds)} 
                          />
                        ))
                      )
                    ) : (
                      <div className="h-full flex flex-col items-center justify-center text-slate-500 italic text-center p-8 space-y-4">
                        <i className="fas fa-magnifying-glass-chart text-3xl opacity-20"></i>
                        <p>Analysis will appear here...</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        ) : (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-3xl font-bold text-white">Saved Highlights</h2>
                <p className="text-slate-500">Your favorite moments collection.</p>
              </div>
            </div>
            {gallery.length === 0 ? (
              <div className="h-[50vh] flex flex-col items-center justify-center text-center space-y-4">
                <i className="fas fa-heart text-3xl text-slate-600"></i>
                <h3 className="text-xl font-semibold text-slate-300">Nothing saved yet</h3>
                <button onClick={() => setActiveTab('analysis')} className="mt-4 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold transition-all">Go to Analysis</button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredGallery.map((item) => (
                  <HighlightCard 
                    key={item.id} 
                    highlight={item} 
                    isActive={false} 
                    isSaved={true}
                    onRemove={() => handleRemoveFromGallery(item.id)}
                    onClick={() => {}}
                    sourceInfo={item.sourceFileName}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
