import { PanelSection, PanelSectionRow, ButtonItem, Spinner } from '@decky/ui';
import { FaDownload, FaPlay, FaStop, FaNetworkWired, FaSyncAlt } from 'react-icons/fa';
import { DualStatusPanel } from './DualStatusPanel';
import { WebConsoleInfo } from './WebConsoleInfo';
import { ErrorBanner } from './ErrorBanner';
import { useEasyTier } from '../hooks/useEasyTier';

export const EasyTierPanel: React.FC = () => {
  const {
    status,
    loading,
    updating,
    error,
    installProgress,
    updateInfo,
    installEasyTier,
    startEasyTier,
    stopEasyTier,
    updateEasyTier
  } = useEasyTier();

  const noTunTip = (
    <PanelSectionRow>
      <div style={{
        padding: '12px',
        fontSize: '12px',
        color: 'var(--text-secondary)',
        background: 'rgba(255, 165, 0, 0.1)',
        borderRadius: '4px',
        lineHeight: '1.5'
      }}>
        ⚠️ Steam Deck 不支持 TUN 模式，请在 Web 控制台中为节点开启
        「无TUN模式 (--no-tun)」，否则会因权限不足导致节点异常。
      </div>
    </PanelSectionRow>
  );

  const versionBar = (
    <PanelSectionRow>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '12px',
        color: 'var(--text-secondary)',
        padding: '4px 0'
      }}>
        <span>版本: v{status.installed_version || '未知'}</span>
        {updateInfo?.update_available && (
          <span style={{ color: 'var(--text-success)' }}>
            新版本 v{updateInfo.latest_version} 可用
          </span>
        )}
      </div>
    </PanelSectionRow>
  );

  const updateButton = updateInfo?.update_available ? (
    <PanelSectionRow>
      <ButtonItem
        layout="below"
        onClick={updateEasyTier}
        disabled={updating}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {updating ? <Spinner /> : <FaSyncAlt />}
          {updating ? '更新中...' : `更新到 v${updateInfo.latest_version}`}
        </div>
      </ButtonItem>
    </PanelSectionRow>
  ) : null;

  const renderUninstalledState = () => (
    <PanelSection title="EasyTier 未安装">
      <PanelSectionRow>
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>
            <FaDownload />
          </div>
          <h3>欢迎使用 Decky EasyTier</h3>
          <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
            需要下载EasyTier：
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
            message="安装失败，请检查网络连接后重试。"
            onRetry={installEasyTier}
          />
        </PanelSectionRow>
      )}
    </PanelSection>
  );

  const renderStoppedState = () => (
    <PanelSection title="EasyTier 服务已停止">
      {versionBar}

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
            2. 启动EasyTier节点
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

      {updateButton}

      {noTunTip}

      {error && (
        <PanelSectionRow>
          <ErrorBanner message={error} onRetry={startEasyTier} />
        </PanelSectionRow>
      )}
    </PanelSection>
  );

  const renderRunningState = () => (
    <PanelSection title="EasyTier 服务运行中">
      {versionBar}

      <PanelSectionRow>
        <div style={{ color: 'var(--text-success)', textAlign: 'center', padding: '8px' }}>
          <strong>✓ 服务运行正常</strong>
        </div>
      </PanelSectionRow>

      <DualStatusPanel status={status} />

      <WebConsoleInfo ip={status.ip} />

      {noTunTip}

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

      {updateInfo?.update_available && (
        <PanelSectionRow>
          <div style={{
            padding: '8px 12px',
            fontSize: '12px',
            color: 'var(--text-success)',
            textAlign: 'center'
          }}>
            新版本 v{updateInfo.latest_version} 可用，请停止服务后更新
          </div>
        </PanelSectionRow>
      )}

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
          警告：Web服务运行中，但EasyTier节点未连接。
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
