import { useRef } from 'react';
import { motion, MotionValue, useTransform } from 'framer-motion';

interface Props {
  scrollProgress: MotionValue<number>;
}

const AuditEngine = ({ scrollProgress }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // 控制 Audit 报告面板的平滑出现 (假设在页面 1/2 到 3/4 处)
  const panelOpacity = useTransform(scrollProgress, [0.6, 0.65], [0, 1]);
  const panelScale = useTransform(scrollProgress, [0.6, 0.65], [0.8, 1]);

  return (
    <section ref={containerRef} style={{ height: '150vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      <div style={{ position: 'relative', width: '600px', height: '500px', margin: '0 auto' }}>
        
        {/* 背景辅助线 */}
        <div style={{
          position: 'absolute', top: '200px', left: 0, width: '100%', height: '1px',
          background: 'var(--line-color)', zIndex: 0
        }}/>

        {/* 逻辑线分叉与汇合动效 */}
        <svg width="100%" height="100%" viewBox="0 0 600 500" style={{ position: 'relative', zIndex: 1 }}>
          <path d="M300 0 L300 50 L100 150 L100 250 L300 350 L300 500 M300 50 L500 150 L500 250 L300 350" fill="none" stroke="var(--primary)" strokeWidth="2" opacity="0.3" />
          
          {/* 模拟源源不断的对比粒子 */}
          <motion.circle r="6" fill="var(--primary)"
            animate={{ offsetDistance: ["0%", "100%"] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            style={{ offsetPath: "path('M300 0 L300 50 L100 150 L100 250 L300 350 L300 500')", filter: 'drop-shadow(0 0 6px var(--primary))' }}
          />
          <motion.circle r="6" fill="var(--text-muted)"
            animate={{ offsetDistance: ["0%", "100%"] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear", delay: 1.5 }}
            style={{ offsetPath: "path('M300 0 L300 50 L500 150 L500 250 L300 350 L300 500')" }}
          />
        </svg>

        <div style={{ position: 'absolute', top: '200px', left: '0', transform: 'translateY(-50%)', textAlign: 'center', width: '200px' }}>
          <div className="hud-panel" style={{ padding: '0.5rem', display: 'inline-block', fontSize: '0.85rem', color: 'var(--primary)' }}>
            SOURCE CODE
          </div>
        </div>
        <div style={{ position: 'absolute', top: '200px', right: '0', transform: 'translateY(-50%)', textAlign: 'center', width: '200px' }}>
          <div className="hud-panel" style={{ padding: '0.5rem', display: 'inline-block', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            LOCALE FILES
          </div>
        </div>

        {/* 动态报告面板 - 定位于汇合点 */}
        <motion.div 
          className="hud-panel"
          style={{ 
            position: 'absolute', 
            top: '350px', 
            left: '50%', 
            x: '-50%',
            y: '-50%',
            padding: '1.5rem 2rem',
            opacity: panelOpacity,
            scale: panelScale,
            width: '320px',
            textAlign: 'center',
            zIndex: 10
          }}
        >
          <div style={{ fontFamily: 'Technical', fontSize: '1.1rem', color: 'var(--text)', marginBottom: '0.5rem' }}>
            AUDIT REPORT
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            <span>MISSING: <span style={{ color: 'var(--accent)' }}>5</span></span>
            <span>DEAD KEYS: <span style={{ color: 'var(--primary)' }}>1</span></span>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default AuditEngine;
