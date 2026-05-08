import { useEffect, useState } from 'react';

const CHARS = ['{', '}', '[', ']', 't(', '"', "'", 'i18n', 'key', ';', '=>'];

const SingleParticle = ({ p }: { p: any }) => {
  return (
    <div
      style={{
        position: 'absolute',
        left: `${p.xOffset}px`,
        opacity: 0.6,
        color: 'var(--primary)',
        textShadow: '0 0 8px var(--primary-glow)',
        fontFamily: 'Technical',
        fontSize: '0.85rem',
        whiteSpace: 'nowrap',
        filter: 'blur(0.5px)',
        animation: `fall ${p.speed}s linear infinite`,
        animationDelay: `${p.delay}s`
      }}
    >
      {p.char}
    </div>
  );
};

const DataParticle = () => {
  const [particles, setParticles] = useState<any[]>([]);

  useEffect(() => {
    // 纯 CSS 动画不需要动态计算进程，直接渲染 DOM 即可
    const initialParticles = Array.from({ length: 30 }).map((_, index) => {
      const speed = 10 + Math.random() * 10; // 10s - 20s
      return {
        id: index,
        char: CHARS[Math.floor(Math.random() * CHARS.length)],
        xOffset: (Math.random() - 0.5) * 60,
        speed: speed,
        delay: -(Math.random() * speed) // CSS animation-delay 完美支持负数
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
      userSelect: 'none'
    }}>
      {particles.map(p => (
        <SingleParticle key={p.id} p={p} />
      ))}
    </div>
  );
};

export default DataParticle;
