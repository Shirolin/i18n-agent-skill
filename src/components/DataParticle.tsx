import { useEffect, useState } from 'react';
import { motion, MotionValue } from 'framer-motion';

const CHARS = ['{', '}', '[', ']', 't(', '"', "'", 'i18n', 'key', ';', '=>'];

interface ParticleProps {
  scrollProgress?: MotionValue<number>;
}

const SingleParticle = ({ p }: { p: any }) => {
  return (
    <motion.div
      animate={{ y: ['-10vh', '110vh'] }}
      transition={{ duration: p.speed, repeat: Infinity, ease: 'linear', delay: p.delay }}
      style={{
        position: 'absolute',
        x: p.xOffset,
        opacity: 0.6,
        color: 'var(--primary)',
        textShadow: '0 0 8px var(--primary-glow)',
        fontFamily: 'Technical',
        fontSize: '0.85rem',
        whiteSpace: 'nowrap',
        filter: 'blur(0.5px)'
      }}
    >
      {p.char}
    </motion.div>
  );
};

const DataParticle = ({}: ParticleProps) => {
  const [particles, setParticles] = useState<any[]>([]);

  useEffect(() => {
    // 初始化生成一批粒子，避免开始时的空窗期
    const initialParticles = Array.from({ length: 30 }).map(() => {
      const speed = 10 + Math.random() * 10; // 10s - 20s
      return {
        id: Math.random(),
        char: CHARS[Math.floor(Math.random() * CHARS.length)],
        xOffset: (Math.random() - 0.5) * 60,
        speed: speed,
        delay: -(Math.random() * speed) // 随机负延迟，使粒子在加载时就分布在屏幕各处
      };
    });
    setParticles(initialParticles);
  }, []);

  return (
    <div 
      aria-hidden="true"
      style={{
      position: 'fixed',
      top: 0,
      left: 'calc(50% - 20px)',
      width: 0,
      height: '100vh',
      zIndex: 2,
      pointerEvents: 'none',
      userSelect: 'none',
      WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)',
      maskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)'
    }}>
      {particles.map(p => (
        <SingleParticle key={p.id} p={p} />
      ))}
    </div>
  );
};

export default DataParticle;
