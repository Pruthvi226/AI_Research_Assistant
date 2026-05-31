import React, { useState } from 'react';
import axios from 'axios';
import { Settings, Shield, Key, Check, HelpCircle } from 'lucide-react';

const SettingsPanel = ({ settings, onSave }) => {
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await axios.post('/settings', {
        gemini_api_key: apiKey.trim()
      });
      setSuccess(true);
      setApiKey(""); // Clear local input
      onSave(); // Reload parent settings
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-full flex flex-col p-6 bg-[#0a0a0c] overflow-y-auto">
      {/* Header */}
      <div className="mb-8 select-none">
        <h2 className="text-2xl font-bold font-['Outfit'] tracking-tight text-white flex items-center gap-2">
          <Settings size={24} className="text-indigo-400" /> System Settings
        </h2>
        <p className="text-xs text-slate-500 mt-1">Configure advanced artificial intelligence endpoints and API credentials.</p>
      </div>

      <div className="max-w-2xl grid grid-cols-1 gap-6">
        {/* Main Settings Card */}
        <div className="glass-panel p-6 border-white/5 bg-white/[0.005]">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Key size={16} className="text-indigo-400" /> Google Gemini API Credentials
          </h3>
          
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 font-medium mb-2">
                Gemini API Key
              </label>
              <input 
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={settings.has_key ? `Active: ${settings.masked_key}` : "Enter your Google Gemini API key..."}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-xs text-white outline-none focus:border-indigo-500/50 transition-colors"
              />
              <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">
                Credentials are saved securely in your local environment. Offloading heavy model processing to the cloud shrinks your Docker footprint, speeds up operations, and bypasses context limits.
              </p>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button 
                type="submit"
                disabled={saving || !apiKey.trim()}
                className="btn-primary flex items-center gap-2 text-xs py-2 px-5 shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? "Saving Configuration..." : "Save Credentials"}
              </button>

              {success && (
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1 animate-pulse">
                  <Check size={14} /> Key saved successfully
                </span>
              )}

              {error && (
                <span className="text-xs font-semibold text-red-400">
                  {error}
                </span>
              )}
            </div>
          </form>
        </div>

        {/* Security / Help Card */}
        <div className="glass-panel p-6 border-white/5 bg-indigo-500/[0.005] flex items-start gap-4">
          <Shield size={24} className="text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-semibold text-slate-200 mb-1">Encrypted Local Keyring</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed mb-4">
              Your API keys are stored in a local configuration database and never shared. If you don't have a Google Gemini key, you can acquire one for free at Google AI Studio.
            </p>
            <a 
              href="https://aistudio.google.com/"
              target="_blank" 
              rel="noopener noreferrer"
              className="text-[10px] font-bold text-indigo-400 hover:text-indigo-300 uppercase tracking-wider flex items-center gap-1 hover:underline"
            >
              Get Free Gemini API Key <HelpCircle size={10} />
            </a>
          </div>
        </div>

      </div>
    </div>
  );
};

export default SettingsPanel;
