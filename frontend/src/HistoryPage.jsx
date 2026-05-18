import React, { useEffect, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function HistoryPage() {
  const [jobs, setJobs] = useState([]);

  async function loadJobs() {
    const response = await fetch(`${API_URL}/jobs`);
    const data = await response.json();
    setJobs(data);
  }

  useEffect(() => {
    loadJobs();
  }, []);

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Historique</p>
        <h1>Historique des projets</h1>
      </section>

      <section className="card">
        <div className="historyList">
          {jobs.map((job) => (
            <div key={job.job_id} className="historyItem">
              <div>
                <strong>{job.filename}</strong>

                <p>
                  {job.status} · {job.language || '—'} ·{' '}
                  {job.duration
                    ? `${Math.round(job.duration)}s`
                    : '—'}
                </p>
              </div>

              <div className="downloads">
                <a href={`${API_URL}/download/${job.job_id}/txt`}>
                  TXT
                </a>

                <a href={`${API_URL}/download/${job.job_id}/srt`}>
                  SRT
                </a>

                <a href={`${API_URL}/download/${job.job_id}/json`}>
                  JSON
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}