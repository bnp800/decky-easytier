import { useState } from 'react';
import { PanelSectionRow, ButtonItem } from '@decky/ui';
import { FaQrcode, FaCopy, FaExternalLinkAlt, FaMobileAlt, FaDesktop, FaCheck } from 'react-icons/fa';

interface QRCodeDisplayProps {
  qrCode?: string;
  ip?: string;
  onCopy?: () => void;
}

export const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({
  qrCode,
  ip,
  onCopy
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!ip) return;

    const url = `http://${ip}:11211`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      onCopy?.();
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy:', e);
    }
  };

  const openInBrowser = () => {
    if (!ip) return;
    const url = `http://${ip}:11211`;
    window.open(url, '_blank');
  };

  return (
    <div className="qr-code-display">
      <PanelSectionRow>
        <div className="qr-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FaQrcode />
          <strong>手机扫描二维码访问</strong>
        </div>
      </PanelSectionRow>

      {qrCode ? (
        <>
          <PanelSectionRow>
            <div className="qr-image-container" style={{ textAlign: 'center', padding: '16px' }}>
              <img
                src={`data:image/svg+xml;base64,${qrCode}`}
                alt="QR Code"
                style={{ maxWidth: '200px', height: 'auto' }}
              />
            </div>
          </PanelSectionRow>

          <PanelSectionRow>
            <div className="qr-actions" style={{ display: 'flex', gap: '8px' }}>
              <ButtonItem onClick={handleCopy}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {copied ? <FaCheck /> : <FaCopy />}
                  {copied ? '已复制' : '复制地址'}
                </div>
              </ButtonItem>

              <ButtonItem onClick={openInBrowser}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FaExternalLinkAlt />
                  在浏览器打开
                </div>
              </ButtonItem>
            </div>
          </PanelSectionRow>

          <PanelSectionRow>
            <div className="qr-info" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              <div style={{ marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <FaMobileAlt />
                  <strong>手机操作：</strong>
                </div>
                <ul style={{ marginLeft: '24px', marginTop: '4px' }}>
                  <li>连接与Steam Deck相同的WiFi</li>
                  <li>使用相机扫描二维码</li>
                  <li>在浏览器中配置网络</li>
                </ul>
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <FaDesktop />
                  <strong>Steam Deck浏览器：</strong>
                </div>
                <ul style={{ marginLeft: '24px', marginTop: '4px' }}>
                  <li>点击"在浏览器打开"</li>
                  <li>或者访问：
                    <code style={{ display: 'block', marginTop: '4px', padding: '4px', background: 'var(--bg-secondary)' }}>
                      http://{ip}:11211
                    </code>
                  </li>
                </ul>
              </div>
            </div>
          </PanelSectionRow>
        </>
      ) : (
        <>
          <PanelSectionRow>
            <div style={{ textAlign: 'center', padding: '16px' }}>
              <div style={{ marginBottom: '8px', color: 'var(--text-secondary)' }}>
                二维码功能不可用，请手动访问：
              </div>
              <code style={{ display: 'block', padding: '8px', background: 'var(--bg-secondary)', wordBreak: 'break-all' }}>
                http://{ip}:11211
              </code>
            </div>
          </PanelSectionRow>

          <PanelSectionRow>
            <div className="qr-actions" style={{ display: 'flex', gap: '8px' }}>
              <ButtonItem onClick={handleCopy}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {copied ? <FaCheck /> : <FaCopy />}
                  {copied ? '已复制' : '复制地址'}
                </div>
              </ButtonItem>

              <ButtonItem onClick={openInBrowser}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FaExternalLinkAlt />
                  在浏览器打开
                </div>
              </ButtonItem>
            </div>
          </PanelSectionRow>
        </>
      )}
    </div>
  );
};