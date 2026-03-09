import React, { useRef } from 'react';
import { uploadPaper } from '../api';

function UploadPaper({ onSuccess, onError, onStart, onEnd, disabled }) {
  const inputRef = useRef(null);

  const handleFileChange = async (e) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      onError({ message: 'Please select a PDF file.' });
      return;
    }
    onStart();
    try {
      const data = await uploadPaper(file);
      onSuccess(data);
    } catch (err) {
      const message = err.response?.data?.error || err.message || 'Upload failed';
      onError({ message });
    } finally {
      onEnd();
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-paper-200 shadow-sm p-4">
      <h2 className="font-display text-lg text-paper-900 mb-3">Upload Paper</h2>
      <label className="block">
        <span className="sr-only">Choose PDF</span>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          disabled={disabled}
          className="block w-full text-sm text-paper-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-accent file:text-white file:font-medium hover:file:bg-accent-light disabled:opacity-50"
        />
      </label>
      <p className="mt-2 text-xs text-paper-500">
        Upload a research paper PDF to get a summary, insights, and chat with the content.
      </p>
    </div>
  );
}

export default UploadPaper;
