import { motion, useScroll, useTransform, useSpring } from 'framer-motion';
import Hero from './components/Hero';
import DataParticle from './components/DataParticle';
import ScannerStation from './components/ScannerStation';
import PrivacyPool from './components/PrivacyPool';
import AuditEngine from './components/AuditEngine';
import FinalEvolution from './components/FinalEvolution';

function App() {
  // 全局滚动进度
  const { scrollYProgress } = useScroll();
  
  // 增加弹性，让滚动更丝滑
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  // 动态导管充能高度
  const pipelineHeight = useTransform(smoothProgress, [0, 1], ['0%', '100%']);

  return (
    <div className="pipeline-container" style={{ position: 'relative' }}>
      {/* 贯穿全屏的动态导管 (The Spine) */}
      <div style={{
        position: 'fixed',
        left: '50%',
        top: 0,
        bottom: 0,
        width: '2px',
        backgroundColor: 'var(--line-color)',
        transform: 'translateX(-50%)',
        zIndex: 0,
      }}>
        {/* 发光充能条 */}
        <motion.div 
          style={{
            width: '100%',
            height: pipelineHeight,
            backgroundColor: 'var(--primary)',
            boxShadow: '0 0 15px var(--primary), 0 0 30px var(--primary-glow)',
          }}
        />
      </div>

      <DataParticle scrollProgress={smoothProgress} />

      <main style={{ position: 'relative', zIndex: 1 }}>
        <Hero />
        <ScannerStation scrollProgress={smoothProgress} />
        <PrivacyPool scrollProgress={smoothProgress} />
        <AuditEngine scrollProgress={smoothProgress} />
        <FinalEvolution scrollProgress={smoothProgress} />
      </main>
    </div>
  );
}

export default App;
