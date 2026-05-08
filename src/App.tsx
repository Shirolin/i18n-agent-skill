import Hero from './components/Hero';
import DataParticle from './components/DataParticle';
import ScannerStation from './components/ScannerStation';
import PrivacyPool from './components/PrivacyPool';
import AuditEngine from './components/AuditEngine';
import FinalEvolution from './components/FinalEvolution';

function App() {
  return (
    <div className="pipeline-container">
      {/* 贯穿全屏的逻辑导向线 */}
      <div 
        className="logic-line"
        style={{
          position: 'fixed',
          left: '50%',
          top: 0,
          bottom: 0,
          width: '1px',
          backgroundColor: 'var(--line-color)',
          boxShadow: '0 0 10px var(--line-color)',
          zIndex: 0,
          transform: 'translateX(-50%)'
        }}
      />

      <DataParticle />

      <main style={{ position: 'relative', zIndex: 1 }}>
        <Hero />
        <ScannerStation />
        <PrivacyPool />
        <AuditEngine />
        <FinalEvolution />
      </main>
    </div>
  );
}

export default App;
