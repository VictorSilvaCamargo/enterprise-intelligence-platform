import { useBackendHealth } from "./hooks/useBackendHealth";
import { MainLayout } from "./layouts/MainLayout";
import { PlatformOverviewPage } from "./pages/PlatformOverviewPage";

export function App() {
  const health = useBackendHealth();

  return (
    <MainLayout connectionState={health.status}>
      <PlatformOverviewPage health={health} />
    </MainLayout>
  );
}

export default App;
