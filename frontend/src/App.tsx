import { useState } from "react";
import { useBackendHealth } from "./hooks/useBackendHealth";
import { MainLayout, type PlatformSection } from "./layouts/MainLayout";
import { PlatformOverviewPage } from "./pages/PlatformOverviewPage";
import { DataManagementSection } from "./pages/dataManagement/DataManagementSection";

export function App() {
  const health = useBackendHealth();
  const [activeSection, setActiveSection] = useState<PlatformSection>("overview");

  return (
    <MainLayout
      connectionState={health.status}
      activeSection={activeSection}
      onNavigateSection={setActiveSection}
    >
      {activeSection === "overview" ? (
        <PlatformOverviewPage health={health} />
      ) : (
        <DataManagementSection />
      )}
    </MainLayout>
  );
}

export default App;
