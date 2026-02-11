import { FaExclamationTriangle } from 'react-icons/fa';
import { PanelSectionRow } from '@decky/ui';

interface ErrorBannerProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onRetry }) => {
  return (
    <PanelSectionRow>
      <div className="error-banner" style={{
        background: 'var(--bg-danger)',
        borderRadius: '4px',
        padding: '12px',
        color: 'var(--text-danger)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <FaExclamationTriangle />
        <div style={{ flex: 1 }}>
          <strong>错误</strong>
          {message && <div style={{ marginTop: '4px', fontSize: '14px' }}>{message}</div>}
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              background: 'var(--text-danger)',
              color: 'var(--bg-danger)',
              border: 'none',
              padding: '4px 12px',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            重试
          </button>
        )}
      </div>
    </PanelSectionRow>
  );
};
