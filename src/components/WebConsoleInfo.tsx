import { useState } from 'react';
import { PanelSectionRow, ButtonItem, Field } from '@decky/ui';
import { FaCopy, FaCheck, FaGlobe } from 'react-icons/fa';

interface WebConsoleInfoProps {
  ip?: string;
}

export const WebConsoleInfo: React.FC<WebConsoleInfoProps> = ({ ip }) => {
  const [copied, setCopied] = useState(false);
  const url = `http://${ip || 'unknown'}:11211`;

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy URL to clipboard', e);
    }
  };

  return (
    <div className="web-console-info">
      <PanelSectionRow>
        <div style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>
          <FaGlobe style={{ marginRight: '6px' }} />
          Web 控制台
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <Field label="访问地址">
          <code style={{ fontSize: '13px' }}>{url}</code>
        </Field>
      </PanelSectionRow>

      <PanelSectionRow>
        <Field label="默认凭据">
          <span>用户名: <strong>admin</strong> / 密码: <strong>admin</strong></span>
        </Field>
      </PanelSectionRow>

      <PanelSectionRow>
        <div style={{
          fontSize: '12px',
          color: 'var(--text-secondary)',
          lineHeight: '1.5',
          padding: '0 16px'
        }}>
          💡 提示：在 Web 控制台中，api-host 需填写 Steam Deck 的 IP 地址（{ip || '未知'}）
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleCopyUrl}
          disabled={!ip}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {copied ? <FaCheck /> : <FaCopy />}
            {copied ? '已复制' : '复制访问地址'}
          </div>
        </ButtonItem>
      </PanelSectionRow>
    </div>
  );
};
