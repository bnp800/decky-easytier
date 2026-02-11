import { useState } from 'react';
import { PanelSectionRow, ToggleField, ButtonItem } from '@decky/ui';
import { FaSave } from 'react-icons/fa';
import { PluginSettings } from '../types';

interface PluginSettingsPanelProps {
  settings?: PluginSettings;
  onSave: (settings: PluginSettings) => void;
}

export const PluginSettingsPanel: React.FC<PluginSettingsPanelProps> = ({
  settings,
  onSave
}) => {
  const [localSettings, setLocalSettings] = useState<PluginSettings>({
    auto_start: false,
    auto_restart_core: true,
    ...settings
  });

  const hasChanges = JSON.stringify(localSettings) !== JSON.stringify(settings);

  const handleSave = () => {
    onSave(localSettings);
  };

  return (
    <div className="plugin-settings-panel">
      <PanelSectionRow>
        <ToggleField
          label="开机自动启动"
          description="Steam Deck启动时自动启动EasyTier服务"
          checked={localSettings.auto_start}
          onChange={(value: boolean) =>
            setLocalSettings(prev => ({ ...prev, auto_start: value }))
          }
          disabled={!settings}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <ToggleField
          label="Core崩溃后自动重启"
          description="当easytier-core进程异常退出时自动重启"
          checked={localSettings.auto_restart_core}
          onChange={(value: boolean) =>
            setLocalSettings(prev => ({ ...prev, auto_restart_core: value }))
          }
          disabled={!settings}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleSave}
          disabled={!hasChanges || !settings}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FaSave />
            保存设置
          </div>
        </ButtonItem>
      </PanelSectionRow>
    </div>
  );
};