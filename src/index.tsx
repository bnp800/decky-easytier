import { definePlugin } from "@decky/api";
import { FaNetworkWired } from "react-icons/fa";
import { PanelSection, PanelSectionRow } from "@decky/ui";
import { EasyTierPanel } from "./components/EasyTierPanel";

function Content() {
  return (
    <PanelSection title="EasyTier 管理">
      <PanelSectionRow>
        <EasyTierPanel />
      </PanelSectionRow>
    </PanelSection>
  );
}

export default definePlugin(() => {
  console.log("Decky EasyTier Plugin initializing...");

  return {
    // 插件显示名称
    name: "Decky EasyTier",

    // 标题栏显示
    titleView: (
      <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
        Decky EasyTier
      </div>
    ),

    // 主内容
    content: <Content />,

    // 插件图标
    icon: <FaNetworkWired />,

    // 卸载时清理
    onDismount() {
      console.log("Decky EasyTier Plugin unloading...");
    },
  };
});
