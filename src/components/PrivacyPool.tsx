import { useRef } from 'react';
import { motion, MotionValue, useTransform } from 'framer-motion';
import { Shield, Lock } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  scrollProgress: MotionValue<number>;
}

const PrivacyPool = ({ scrollProgress }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  
  // 映射脱敏动效的平滑过渡 (假设在页面 1/4 到 1/2 处)
  const lockOpacity = useTransform(scrollProgress, [0.35, 0.45], [0.2, 1]);
  const lockScale = useTransform(scrollProgress, [0.35, 0.45], [0.8, 1]);
  const textBlur = useTransform(scrollProgress, [0.35, 0.4, 0.45], ['0px', '5px', '0px']);

  // 使用一个技巧：在中间状态模糊时，底层文本发生切换（通过透明度交叉）
  const rawOpacity = useTransform(scrollProgress, [0.35, 0.4], [1, 0]);
  const maskedOpacity = useTransform(scrollProgress, [0.4, 0.45], [0, 1]);

  return (
    <section ref={containerRef} style={{ height: '120vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      
      {/* 限制宽度的双栏对称容器 */}
      <div style={{ width: '100%', maxWidth: '1000px', display: 'flex', alignItems: 'center', gap: '4rem' }}>
        
        {/* 左栏：说明文字 */}
        <div style={{ flex: 1, textAlign: 'right' }}>
          <h3 style={{ color: 'var(--accent)', fontFamily: 'Technical', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.8rem', textShadow: '0 0 10px rgba(210, 153, 34, 0.3)' }}>
            {t('privacy.title')} <Shield size={24} />
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginTop: '1rem', lineHeight: '1.6' }}>
            {t('privacy.desc')}
          </p>
        </div>

        {/* 右栏：脱敏池动画 */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'flex-start' }}>
          <div className="hud-panel" style={{
            width: '320px',
            height: '420px',
            borderColor: 'var(--accent)',
            background: 'rgba(210, 153, 34, 0.05)',
            boxShadow: '0 0 30px rgba(0,0,0,0.5), inset 0 0 20px rgba(210, 153, 34, 0.1)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            {/* 脱敏动效区 */}
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              style={{ 
                fontSize: '0.85rem', 
                fontFamily: 'Technical', 
                color: 'var(--accent)',
                position: 'relative',
                height: '20px',
                width: '100%',
                textAlign: 'center',
                filter: textBlur
              }}
            >
              <motion.span style={{ position: 'absolute', width: '100%', left: 0, opacity: rawOpacity }}>
                sk-proj-a1b2c3d4e5f6...
              </motion.span>
              <motion.span style={{ position: 'absolute', width: '100%', left: 0, opacity: maskedOpacity }}>
                [MASKED_API_KEY]
              </motion.span>
            </motion.div>
            
            <motion.div style={{ marginTop: '2rem', opacity: lockOpacity, scale: lockScale }}>
              <Lock size={48} color="var(--accent)" style={{ filter: 'drop-shadow(0 0 8px rgba(210, 153, 34, 0.6))' }} />
            </motion.div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default PrivacyPool;
