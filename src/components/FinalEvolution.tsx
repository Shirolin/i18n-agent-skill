import { useRef } from 'react';
import { motion, MotionValue, useTransform } from 'framer-motion';
import { CheckCircle2, RotateCcw } from 'lucide-react';
import { useTranslation, Trans } from 'react-i18next';

interface Props {
  scrollProgress: MotionValue<number>;
}

const FinalEvolution = ({ scrollProgress }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  
  // 控制最终状态的显现
  const iconScale = useTransform(scrollProgress, [0.8, 0.9], [0.5, 1]);
  const crystalsOpacity = useTransform(scrollProgress, [0.85, 0.95], [0, 1]);
  const crystalsY = useTransform(scrollProgress, [0.85, 0.95], [30, 0]);

  // 模拟并发同步的语言标识
  const syncedLangs = ['EN', 'ZH', 'JA'];

  return (
    <section ref={containerRef} style={{ 
      height: '150vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      position: 'relative' 
    }}>
      <div className="hud-panel" style={{ textAlign: 'center', maxWidth: '600px', zIndex: 10, padding: '3rem 4rem', background: 'var(--bg-panel)' }}>
        <motion.div style={{ scale: iconScale, display: 'inline-block' }}>
          <CheckCircle2 size={72} color="var(--primary)" style={{ marginBottom: '1.5rem', filter: 'drop-shadow(0 0 12px var(--primary-glow))' }} />
        </motion.div>
        
        <h2 style={{ fontFamily: 'Technical', color: 'var(--primary)', letterSpacing: '0.25em', fontSize: '1.8rem' }}>
          {t('evolution.title')}
        </h2>
        <p style={{ color: 'var(--text-muted)', margin: '1.5rem 0 0', lineHeight: '1.8', fontSize: '1rem' }}>
          <Trans i18nKey="evolution.desc">
            Manual Commit confirms final translation. All items are locked into <strong style={{ color: 'var(--text)' }}>L3 Approved State</strong>, ensuring immutable consistency and robust evolution.
          </Trans>
        </p>
      </div>

      {/* 真理晶体阵列 (并发多语言) */}
      <motion.div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(3, 1fr)', 
        gap: '40px', 
        marginTop: '3.5rem',
        opacity: crystalsOpacity,
        y: crystalsY,
        zIndex: 10 // 确保覆盖逻辑线
      }}>
        {syncedLangs.map(lang => (
          <div key={lang} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div className="hud-panel" style={{ 
              width: '80px', 
              height: '80px', 
              transform: 'rotate(45deg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              // 关键修复：使用不透明深色底色阻断逻辑线穿透
              background: '#0a0d13', 
              boxShadow: '0 0 20px rgba(0,0,0,0.8), inset 0 0 15px rgba(88, 166, 255, 0.1)',
              border: '1px solid rgba(88, 166, 255, 0.4)'
            }}>
              <span style={{ 
                transform: 'rotate(-45deg)', 
                fontSize: '1rem', 
                color: '#ffffff', 
                fontFamily: 'Technical', 
                fontWeight: 'bold',
                textShadow: '0 0 8px rgba(88, 166, 255, 0.8)'
              }}>L3</span>
            </div>
            {/* 赋予节点实际业务语义 */}
            <span style={{ 
              marginTop: '1.5rem', 
              fontFamily: 'Technical', 
              fontSize: '0.75rem', 
              color: 'var(--primary)',
              letterSpacing: '0.1em',
              opacity: 0.8
            }}>{t('evolution.sync')}: {lang}</span>
          </div>
        ))}
      </motion.div>

      {/* 安装指引 */}
      <div style={{ 
        marginTop: '6rem',
        zIndex: 10,
        position: 'relative'
      }}>
        <div className="hud-panel" style={{ 
          padding: '1rem 2rem', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '1.5rem',
          background: '#0a0d13',
          border: '1px solid rgba(88, 166, 255, 0.4)',
          boxShadow: '0 0 20px rgba(0,0,0,0.8), inset 0 0 15px rgba(88, 166, 255, 0.1)'
        }}>
          <span style={{ color: 'var(--text-muted)', fontFamily: 'Technical', userSelect: 'none' }}>$</span>
          <code style={{ color: 'var(--primary)', fontFamily: 'Technical', fontSize: '1rem', letterSpacing: '0.05em' }}>
            npx skills add Shirolin/i18n-agent-skill
          </code>
        </div>
      </div>

      {/* 莫比乌斯环回流逻辑 */}
      <div style={{ 
        marginTop: '5rem', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center',
        color: '#8b949e', // 提升对比度
        zIndex: 10,
        position: 'relative'
      }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
          style={{ 
            background: 'var(--bg)', // 阻断逻辑线
            borderRadius: '50%', 
            padding: '4px',
            display: 'flex'
          }}
        >
          <RotateCcw size={28} color="rgba(88, 166, 255, 0.7)" style={{ filter: 'drop-shadow(0 0 5px rgba(88, 166, 255, 0.3))' }} />
        </motion.div>
        
        {/* 呼吸灯效与高亮文字 */}
        <motion.span 
          animate={{ opacity: [0.6, 1, 0.6], textShadow: ['0 0 0px var(--primary)', '0 0 8px var(--primary)', '0 0 0px var(--primary)'] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          style={{ 
            fontFamily: 'Technical', 
            fontSize: '0.85rem', 
            letterSpacing: '0.15em',
            marginTop: '1rem',
            color: '#c9d1d9',
            background: 'var(--bg)', // 阻断逻辑线
            padding: '0 10px'
          }}
        >
          {t('evolution.restarting')}
        </motion.span>
      </div>

      <footer style={{ 
        position: 'absolute', 
        bottom: '2rem', 
        width: '100%', 
        textAlign: 'center', 
        color: 'var(--text-muted)',
        fontSize: '0.85rem',
        opacity: 0.6,
        zIndex: 10,
        background: 'var(--bg)' // 防止线穿过底部文字
      }}>
        {t('evolution.footer')}
      </footer>
    </section>
  );
};

export default FinalEvolution;
