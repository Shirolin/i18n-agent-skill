import { useRef } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, RotateCcw } from 'lucide-react';
import { useScrollProgress } from '../hooks/useScrollProgress';

const FinalEvolution = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const progress = useScrollProgress(containerRef);

  return (
    <section ref={containerRef} style={{ 
      height: '150vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      position: 'relative' 
    }}>
      <div style={{ textAlign: 'center', maxWidth: '600px', zIndex: 10 }}>
        <motion.div
          animate={{ scale: progress > 0.5 ? [1, 1.2, 1] : 1 }}
          transition={{ duration: 0.5 }}
        >
          <CheckCircle2 size={60} color="var(--primary)" style={{ marginBottom: '1rem' }} />
        </motion.div>
        
        <h2 style={{ fontFamily: 'Technical', color: 'var(--primary)', letterSpacing: '0.2em' }}>
          L3 TRUTH SECURED
        </h2>
        <p style={{ color: 'var(--text-muted)', margin: '1.5rem 0', lineHeight: '1.6' }}>
          人工 Commit 触发状态跃迁。所有翻译项已结晶为 L3 级 Approved 状态，实现逻辑幂等，驱动项目持续演进。
        </p>
      </div>

      {/* 真理晶体阵列 */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(3, 1fr)', 
        gap: '20px', 
        marginTop: '2rem',
        opacity: progress > 0.4 ? 1 : 0,
        transition: 'opacity 1s'
      }}>
        {[1, 2, 3].map(i => (
          <div key={i} style={{ 
            width: '100px', 
            height: '100px', 
            border: '1px solid var(--primary)', 
            background: 'rgba(88, 166, 255, 0.1)',
            transform: 'rotate(45deg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <span style={{ transform: 'rotate(-45deg)', fontSize: '0.7rem', color: 'var(--primary)' }}>L3</span>
          </div>
        ))}
      </div>

      {/* 莫比乌斯环回流逻辑 */}
      <div style={{ 
        marginTop: '5rem', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center',
        color: 'var(--text-muted)' 
      }}>
        <RotateCcw size={30} className="spin" style={{ marginBottom: '1rem' }} />
        <span style={{ fontFamily: 'Technical', fontSize: '0.8rem' }}>RESTARTING CYCLE...</span>
      </div>

      <footer style={{ 
        position: 'absolute', 
        bottom: '2rem', 
        width: '100%', 
        textAlign: 'center', 
        color: 'var(--text-muted)',
        fontSize: '0.8rem'
      }}>
        © 2026 i18n-agent-skill | Continuous Globalization, Continuous Evolution.
      </footer>
    </section>
  );
};

export default FinalEvolution;
