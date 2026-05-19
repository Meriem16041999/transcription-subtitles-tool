import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Upload, FileText, Download } from 'lucide-react';
import './styles.css';
 

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const AVAILABLE_LANGUAGES = [
  { code: 'en', label: 'Anglais' },
  { code: 'es', label: 'Espagnol' },
  { code: 'ar', label: 'Arabe' },
];

function HomePage() {
  const [page, setPage] = useState('home');
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState('fr');
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [makeTranscription, setMakeTranscription] = useState(true);
  const [makeTranslation, setMakeTranslation] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [targetLanguages, setTargetLanguages] = useState(['en']);
  const [tcIn, setTcIn] = useState('00:00:00:00');
  const videoRef = useRef(null);

  function seekTo(seconds) {
    if (!videoRef.current) return;
    videoRef.current.currentTime = seconds;
    videoRef.current.play();
  }
 const [currentTime, setCurrentTime] = useState(0);

  function updateSegmentText(index, newText) {
    setJob((previousJob) => {
      const updatedSegments = [...previousJob.result.segments];

      updatedSegments[index] = {
        ...updatedSegments[index],
        text: newText,
      };

      return {
        ...previousJob,
        result: {
          ...previousJob.result,
          segments: updatedSegments,
        },
      };
    });
  }

 async function loadJobs() {
  const response = await fetch(`${API_URL}/jobs`);
  const data = await response.json();
  setJobs(data);
}
useEffect(() => {
  if (!job?.job_id) return;
  if (job.status === 'Terminé' || job.status === 'Erreur') return;

  const interval = setInterval(async () => {
    const response = await fetch(`${API_URL}/jobs/${job.job_id}`);
    const data = await response.json();

    setJob((previous) => ({
      ...previous,
      ...data,
    }));
  }, 5000);

  return () => clearInterval(interval);
}, [job?.job_id, job?.status]);

useEffect(() => {
  loadJobs();
}, []); 
  function updateSegmentSpeaker(index, newSpeaker) {
  setJob((previousJob) => {
    const updatedSegments = [...previousJob.result.segments];

    updatedSegments[index] = {
      ...updatedSegments[index],
      speaker: newSpeaker,
    };

    return {
      ...previousJob,
      result: {
        ...previousJob.result,
        segments: updatedSegments,
      },
    };
  });
}

async function deleteJob(jobId) {
  const confirmed = window.confirm("Supprimer cet historique ?");
  if (!confirmed) return;

  await fetch(`${API_URL}/jobs/${jobId}`, {
    method: "DELETE",
  });

  loadJobs();
}


  async function saveEdits() {
  if (!jobId) return;

  await fetch(`${API_URL}/jobs/${jobId}/update`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(job.result.segments),
  });

  alert("Modifications sauvegardées");
}
  function toggleTargetLanguage(lang) {
    setTargetLanguages((previous) => {
      if (previous.includes(lang)) {
        return previous.filter((item) => item !== lang);
      }
      return [...previous, lang];
    });
  }

  async function handleSubmit(event) {
  event.preventDefault();
  if (!file) return;

  if (makeTranslation && targetLanguages.length === 0) {
    setError('Choisis au moins une langue cible.');
    return;
  }

  setLoading(true);
  setError('');
  setJob(null);

  const formData = new FormData();
  formData.append('file', file);
  formData.append('make_transcription', String(makeTranscription));
  formData.append('make_translation', String(makeTranslation));
  formData.append('target_languages', JSON.stringify(targetLanguages));
  formData.append('tc_in', tcIn);

  try {
    const response = await fetch(`${API_URL}/transcribe?language=${language}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.detail || 'Erreur pendant la transcription');
    }

    const data = await response.json();
    setJob(data);
    loadJobs();
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

  const jobId = job?.job_id;
  const segments = job?.result?.segments || [];
  const translatedFiles = job?.result?.translated_files || {};
  const dubFiles = job?.result?.dub_files || {};
  const filteredSegments = segments.filter((segment) =>
  segment.text.toLowerCase().includes(searchQuery.toLowerCase())
);
  return (
    <main className="page">
    <nav className="topNav">
  <button type="button" onClick={() => setPage('home')}>
    Nouvelle transcription
  </button>

  <button type="button" onClick={() => setPage('history')}>
    Historique
  </button>
</nav>
{page === 'history' && (
  <section className="card">
    <h2>Historique des projets</h2>

    <div className="historyList">
      {jobs.map((item) => (
        <div key={item.job_id} className="historyItem">
          <div>
            <strong>{item.filename}</strong>
            <p>
              {item.status} · {item.language || '—'} ·{' '}
              {item.duration ? `${Math.round(item.duration)}s` : '—'}
            </p>
          </div>

          <div className="downloads">
            <a href={`${API_URL}/download/${item.job_id}/txt`}>TXT</a>
            <a href={`${API_URL}/download/${item.job_id}/srt`}>SRT</a>
            <a href={`${API_URL}/download/${item.job_id}/json`}>JSON</a>
            <button type="button" onClick={() => deleteJob(item.job_id)}>
  Supprimer
</button>
          </div>
        </div>
      ))}
    </div>
  </section>
)}
      {page === 'home' && (
  <>
      <section className="hero">
        <p className="eyebrow">Outil interne</p>
        <h1>Transcription, sous-titres et doublage</h1>
        <p className="subtitle">
          Upload une vidéo, génère la transcription, choisis les langues de sous-titres ou de doublage.
        </p>
      </section>

      <section className="card">
        <form onSubmit={handleSubmit} className="form">
          <label className="dropzone">
            <Upload size={36} />
            <span>{file ? file.name : 'Choisir un fichier vidéo ou audio'}</span>
            <input
              type="file"
              accept="video/*,audio/*"
              onChange={(e) => setFile(e.target.files?.[0])}
            />
          </label>

          <div className="row">
            <label>
              Langue source
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="fr">Français</option>
                <option value="en">Anglais</option>
                <option value="ar">Arabe</option>
                <option value="es">Espagnol</option>
                <option value="auto">Auto</option>
              </select>
            </label>

            <button disabled={!file || loading} type="submit">
              {loading ? 'Traitement en cours...' : 'Lancer le traitement'}
            </button>
          </div>
          <label className="checkOption">
         <input
           type="checkbox"
           checked={makeTranscription}
           onChange={(e) => setMakeTranscription(e.target.checked)}
         />
  Générer la transcription
</label>
          <div className="optionsBox">
            <label className="checkOption">
              <input
                type="checkbox"
                checked={makeTranslation}
                onChange={(e) => setMakeTranslation(e.target.checked)}
              />
              Générer les sous-titres multilingues
            </label>
            <label>
  TC IN
  <input
    type="text"
    value={tcIn}
    onChange={(e) => setTcIn(e.target.value)}
    placeholder="01:00:00:00"
  />
</label>
            <div className="languageChoices">
              <span>Langues cibles</span>

              {AVAILABLE_LANGUAGES.map((lang) => (
                <label key={lang.code} className="checkPill">
                  <input
                    type="checkbox"
                    checked={targetLanguages.includes(lang.code)}
                    onChange={() => toggleTargetLanguage(lang.code)}
                  />
                  {lang.label}
                </label>
              ))}
            </div>
          </div>
        </form>
         
        {error && <p className="error">{error}</p>}
      </section>

      {job && (
        <section className="card result">
          <div className="resultHeader">
            <h2>{job.filename}</h2>
            <p className="jobStatus">
  Statut : {job.status}
</p>
{job.error && (
  <p className="error">
    Erreur : {job.error}
  </p>
)}
            <div className="downloads">
              <a href={`${API_URL}/download/${jobId}/txt`}>
                <Download size={16} /> TXT
              </a>

              <a href={`${API_URL}/download/${jobId}/srt`}>
                <Download size={16} /> SRT original
              </a>

              <a href={`${API_URL}/download/${jobId}/json`}>
                <Download size={16} /> JSON
              </a>
              

              {Object.keys(translatedFiles).map((lang) => (
                <a key={lang} href={`${API_URL}/download/${jobId}/srt/${lang}`}>
                  <Download size={16} /> SRT {lang.toUpperCase()}
                </a>
              ))}

              {Object.keys(dubFiles).map((lang) => (
                <a key={lang} href={`${API_URL}/download/${jobId}/dub/${lang}`}>
                  <Download size={16} /> Audio {lang.toUpperCase()}

                </a>
              ))}
              <button onClick={saveEdits}>Sauvegarder corrections</button>
            </div>
          </div>

          {jobId && (
           <video
             ref={videoRef}
             controls
             src={`${API_URL}/media/${jobId}`}
             onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
           style={{ width: '100%', marginBottom: '20px' }}
            />
          )}
          <input
  className="searchInput"
  type="text"
  placeholder="Rechercher dans la transcription..."
  value={searchQuery}
  onChange={(e) => setSearchQuery(e.target.value)}
/>
          <div className="segments">
            {filteredSegments.map((segment, index) => (
               <article
                  key={index}
                  className={`segment ${
                  currentTime >= segment.start && currentTime <= segment.end
                   ? "active"
                     : ""
            }`}
            onClick={() => seekTo(segment.start)}
            style={{ cursor: 'pointer' }}
                >
                 <div className="segmentTop">
  <input
    className="speakerInput"
    value={segment.speaker || "Speaker_0"}
    onChange={(e) => updateSegmentSpeaker(index, e.target.value)}
    onClick={(e) => e.stopPropagation()}
  />

  <span>
    {segment.start.toFixed(2)}s → {segment.end.toFixed(2)}s
  </span>
</div>

                <div className="editableLine">
                  <FileText size={16} />
                  <textarea
                    value={segment.text}
                    onChange={(e) => updateSegmentText(index, e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    rows={2}
                  />
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
      </>
)}
    </main>
  );
}

createRoot(document.getElementById('root')).render(<HomePage />);

