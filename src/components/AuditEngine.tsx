import { useRef } from 'react';
import { motion } from 'framer-motion';
import { useScrollProgress } from '../hooks/useScrollProgress';

const AuditEngine = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const progress = useScrollProgress(containerRef);

  return (
    <section ref={containerRef} style={{ height: '150vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'relative', width: '600px', height: '300px' }}>
        {/* 逻辑线分叉对比动效 */}
        <svg width="100%" height="100%" viewBox="0 0 600 300">
          <path d="M300 0 L300 50 L100 150 L100 250 M300 50 L500 150 L500 250" fill="none" stroke="var(--line-color)" strokeWidth="2" />
          {/* 模拟粒子 */}
          <motion.circle r="4" fill="var(--primary)"
            animate={{ offsetDistance: ["0%", "100%"] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            style={{ offsetPath: "path('M300 0 L300 50 L100 150 L100 250')" }}
          />
          <motion.circle r="4" fill="var(--primary)"
            animate={{ offsetDistance: ["0%", "100%"] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear", delay: 0.5 }}
            style={{ offsetPath: "path('M300 0 L300 50 L500 150 L500 250')" }}
          />
        </svg>

        <div style={{ position: 'absolute', top: '50%', left: '0', textAlign: 'center', width: '200px' }}>
          <div style={{ color: 'var(--primary)', fontSize: '0.8rem' }}>SOURCE CODE</div>
        </div>
        <div style={{ position: 'absolute', top: '50%', right: '0', textAlign: 'center', width: '200px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>LOCALE FILES</div>
        </div>

        <div style={{ 
          position: 'absolute', 
          bottom: '-20%', 
          left: '50%', 
          transform: 'translateX(-50%)',
          backgroundColor: 'rgba(88, 166, 255, 0.1)',
          padding: '1rem',
          borderRadius: '4px',
          border: '1px solid var(--primary)',
          opacity: progress > 0.6 ? 1 : 0
        }}>
          <div style={{ fontFamily: 'Technical', fontSize: '0.8rem' }}>AUDIT: 5 MISSING, 1 DEAD KEY</div>
        </div>
      </div>
    </section>
  );
};

export default AuditEngine;
