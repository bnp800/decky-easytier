import { definePlugin } from '@decky/api';
import { FaNetworkWired } from 'react-icons/fa';
import { EasyTierPanel } from './components/EasyTierPanel';

const styles = `
.et-title{font-size:22px;font-weight:700}.et-label{font-size:13px;font-weight:600;margin-bottom:6px}
.et-muted{color:#aaa;font-size:12px;padding:6px 0}.et-error,.et-warning{border-radius:4px;margin:8px 0;padding:10px;white-space:pre-wrap}
.et-error{background:rgba(190,45,45,.25);color:#ffb4b4}.et-warning{background:rgba(195,135,15,.25);color:#ffd98a}
.et-profile{border:1px solid rgba(255,255,255,.15);border-radius:5px;margin:7px 0;overflow:hidden}.et-profile.selected{border-color:#66c0f4}
.et-actions{display:flex;gap:6px;padding:0 8px 8px}.et-actions button{background:rgba(255,255,255,.12);border:0;border-radius:4px;color:white;padding:8px 14px}.et-actions button:disabled{opacity:.35}
.et-list-editor{display:flex;flex-direction:column;gap:6px}.et-list-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;align-items:end}.et-list-row button{min-width:70px}
.et-textarea,.et-toml{box-sizing:border-box;width:100%;resize:vertical;border:1px solid rgba(255,255,255,.2);border-radius:4px;background:rgba(0,0,0,.35);color:white;padding:9px}
.et-textarea{min-height:72px}.et-toml{min-height:420px;font-family:monospace;font-size:12px}
.et-json,.et-log{overflow:auto;max-height:260px;background:rgba(0,0,0,.3);border-radius:4px;padding:8px;font-size:10px;white-space:pre-wrap;word-break:break-word}`;

export default definePlugin(() => ({
  name: 'Decky EasyTier',
  titleView: <div className="et-title">Decky EasyTier</div>,
  content: <><style>{styles}</style><EasyTierPanel /></>,
  icon: <FaNetworkWired />,
}));
