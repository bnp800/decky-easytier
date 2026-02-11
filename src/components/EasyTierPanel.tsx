import { PanelSection, PanelSectionRow, ButtonItem, Spinner } from '@decky/ui';
import { FaDownload, FaPlay, FaStop, FaNetworkWired } from 'react-icons/fa';
import { DualStatusPanel } from './DualStatusPanel';
import { PluginSettingsPanel } from './PluginSettingsPanel';
import { WebConsoleInfo } from './WebConsoleInfo';
import { ErrorBanner } from './ErrorBanner';
import { useEasyTier } from '../hooks/useEasyTier';

export const EasyTierPanel: React.FC = () => {
  const {
    status,
    loading,
    error,
    installProgress,
    installEasyTier,
    startEasyTier,
    stopEasyTier,
    savePluginSettings
  } = useEasyTier();

  const renderUninstalledState = () => (
    <PanelSection title="EasyTier 未安装">
      <PanelSectionRow>
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>
            <FaDownload />
          </div>
          <h3>欢迎使用 Decky EasyTier</h3>
          <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
            需要下载两个二进制文件：
            <br />
            <code style={{ display: 'block', margin: '8px 0', padding: '8px', background: 'var(--bg-secondary)' }}>
              • easytier-web - Web管理控制台
              <br />
              • easytier-core - VPN节点服务
            </code>
            总大小: ~42MB
          </p>
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={installEasyTier}
          disabled={loading}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {loading ? <Spinner /> : <FaDownload />}
            {loading ? '安装中...' : '安装 EasyTier'}
          </div>
        </ButtonItem>
      </PanelSectionRow>

      {installProgress && (
        <PanelSectionRow>
          <div style={{ padding: '16px' }}>
            <div style={{ marginBottom: '8px' }}>
              {installProgress.message}
            </div>
            <div style={{
              background: 'var(--bg-secondary)',
              borderRadius: '4px',
              height: '8px',
              overflow: 'hidden'
            }}>
              <div style={{
                background: 'var(--text-success)',
                width: `${installProgress.percent}%`,
                height: '100%',
                transition: 'width 0.3s'
              }} />
            </div>
          </div>
        </PanelSectionRow>
      )}

      {error && (
        <PanelSectionRow>
          <ErrorBanner
            message="安装失败，请检查网络连接后重试。也可以手动下载二进制文件并放置到 ~/.local/share/decky-easytier/easytier/ 目录。"
            onRetry={installEasyTier}
          />
        </PanelSectionRow>
      )}
    </PanelSection>
  );

  const renderStoppedState = () => (
    <PanelSection title="EasyTier 服务已停止">
      <PanelSectionRow>
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>
            <FaNetworkWired />
          </div>
          <h3>服务已停止</h3>
          <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
            点击启动后将自动完成：
          </p>
          <div style={{ textAlign: 'left', margin: '16px 0', color: 'var(--text-secondary)' }}>
            1. 启动Web管理控制台<br />
            2. 启动配置服务器（22020）<br />
            3. 启动VPN节点服务
          </div>
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={startEasyTier}
          disabled={loading}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {loading ? <Spinner /> : <FaPlay />}
            {loading ? '启动中...' : '启动 EasyTier'}
          </div>
        </ButtonItem>
      </PanelSectionRow>

      <PanelSectionRow>
        <div style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '12px' }}>
          ⚙️ 插件设置：
        </div>
        <PluginSettingsPanel
          settings={status.plugin_settings}
          onSave={savePluginSettings}
        />
      </PanelSectionRow>

      {error && (
        <PanelSectionRow>
          <ErrorBanner message={error} onRetry={startEasyTier} />
        </PanelSectionRow>
      )}
    </PanelSection>
  );

  const renderRunningState = () => (
    <PanelSection title="EasyTier 服务运行中">
      <PanelSectionRow>
        <div style={{ color: 'var(--text-success)', textAlign: 'center', padding: '8px' }}>
          <strong>✓ 服务运行正常</strong>
        </div>
      </PanelSectionRow>

      <DualStatusPanel status={status} />

      <WebConsoleInfo ip={status.ip} />

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={stopEasyTier}
          disabled={loading}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {loading ? <Spinner /> : <FaStop />}
            {loading ? '停止中...' : '停止 EasyTier'}
          </div>
        </ButtonItem>
      </PanelSectionRow>

      {error && (
        <PanelSectionRow>
          <ErrorBanner message={error} />
        </PanelSectionRow>
      )}
    </PanelSection>
  );

  const renderPartialState = () => (
    <PanelSection title="⚠️ 服务部分运行">
      <DualStatusPanel status={status} />

      <PanelSectionRow>
        <div style={{ color: 'var(--text-warning)' }}>
          警告：Web服务运行中，但VPN节点未连接。
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={stopEasyTier}
          disabled={loading}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {loading ? <Spinner /> : <FaStop />}
            停止服务并重新启动
          </div>
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );

  const renderErrorState = () => (
    <PanelSection title="❌ 服务运行错误">
      <PanelSectionRow>
        <ErrorBanner message={status.error || 'Unknown error occurred'} />
      </PanelSectionRow>

      <DualStatusPanel status={status} />

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={stopEasyTier}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FaStop />
            停止服务
          </div>
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );

  switch (status.overall) {
    case 'uninstalled':
      return renderUninstalledState();
    case 'stopped':
      return renderStoppedState();
    case 'running':
      return renderRunningState();
    case 'partial':
      return renderPartialState();
    case 'error':
      return renderErrorState();
    default:
      return (
        <PanelSection>
          <PanelSectionRow>
            <div style={{ textAlign: 'center', padding: '16px' }}>
              <Spinner />
              <p>正在加载...</p>
            </div>
          </PanelSectionRow>
        </PanelSection>
      );
  }
};
