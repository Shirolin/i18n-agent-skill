import { useRef } from 'react';
import { motion, MotionValue, useTransform } from 'framer-motion';
import { CheckCircle2, RotateCcw } from 'lucide-react';

interface Props {
  scrollProgress: MotionValue<number>;
}

const FinalEvolution = ({ scrollProgress }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // 控制最终状态的显现
  const iconScale = useTransform(scrollProgress, [0.8, 0.9], [0.5, 1]);
  const crystalsOpacity = useTransform(scrollProgress, [0.85, 0.95], [0, 1]);
  const crystalsY = useTransform(scrollProgress, [0.85, 0.95], [30, 0]);

  return (
    <section ref={containerRef} style={{ 
      height: '150vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      position: 'relative' 
    }}>
      <div className="hud-panel" style={{ textAlign: 'center', maxWidth: '600px', zIndex: 10, padding: '3rem 4rem', background: 'var(--bg)' }}>
        <motion.div style={{ scale: iconScale, display: 'inline-block' }}>
          <CheckCircle2 size={72} color="var(--primary)" style={{ marginBottom: '1.5rem', filter: 'drop-shadow(0 0 12px var(--primary-glow))' }} />
        </motion.div>
        
        <h2 style={{ fontFamily: 'Technical', color: 'var(--primary)', letterSpacing: '0.25em', fontSize: '1.8rem' }}>
          L3 TRUTH SECURED
        </h2>
        <p style={{ color: 'var(--text-muted)', margin: '1.5rem 0 0', lineHeight: '1.8', fontSize: '1rem' }}>
          人工 Commit 确认最终翻译。所有翻译项已锁定为 <strong style={{ color: 'var(--text)' }}>L3 终审状态</strong>，确保内容一致且不可篡改，驱动项目稳健演进。
        </p>
      </div>

      {/* 真理晶体阵列 */}
      <motion.div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(3, 1fr)', 
        gap: '30px', 
        marginTop: '3rem',
        opacity: crystalsOpacity,
        y: crystalsY
      }}>
        {[1, 2, 3].map(i => (
          <div key={i} className="hud-panel" style={{ 
            width: '90px', 
            height: '90px', 
            transform: 'rotate(45deg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(88, 166, 255, 0.05)',
            boxShadow: '0 0 15px rgba(88, 166, 255, 0.1)'
          }}>
            <span style={{ 
              transform: 'rotate(-45deg)', 
              fontSize: '1.1rem', 
              color: '#ffffff', 
              fontFamily: 'Technical', 
              fontWeight: 'bold',
              textShadow: '0 0 8px rgba(88, 166, 255, 0.8)'
            }}>L3</span>
          </div>
        ))}
      </motion.div>

      {/* 莫比乌斯环回流逻辑 */}
      <div style={{ 
        marginTop: '6rem', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center',
        color: 'var(--text-muted)' 
      }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
        >
          <RotateCcw size={32} style={{ marginBottom: '1rem', opacity: 0.5 }} />
        </motion.div>
        <span style={{ fontFamily: 'Technical', fontSize: '0.85rem', letterSpacing: '0.1em' }}>RESTARTING CYCLE...</span>
      </div>

      <footer style={{ 
        position: 'absolute', 
        bottom: '2rem', 
        width: '100%', 
        textAlign: 'center', 
        color: 'var(--text-muted)',
        fontSize: '0.85rem',
        opacity: 0.6
      }}>
        © 2026 i18n-agent-skill | Continuous Globalization, Continuous Evolution.
      </footer>
    </section>
  );
};

export default FinalEvolution;
