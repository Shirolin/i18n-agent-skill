import { useRef } from 'react';
import { motion, MotionValue, useTransform } from 'framer-motion';
import { useTranslation } from 'react-i18next';

interface Props {
  scrollProgress: MotionValue<number>;
}

const ScannerStation = ({ scrollProgress }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  
  // 将全局滚动进度映射到局部组件的特定动效
  // 假设 ScannerStation 位于页面顶部到 1/4 处
  const laserTop = useTransform(scrollProgress, [0, 0.25], ['0%', '100%']);
  const highlightColor = useTransform(scrollProgress, [0.1, 0.15], ['var(--text-muted)', 'var(--primary)']);
  const opacityEndonym = useTransform(scrollProgress, [0.2, 0.25], [0, 1]);

  return (
    <section 
      ref={containerRef}
      style={{ 
        height: '150vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        position: 'relative'
      }}
    >
      {/* 限制最大宽度的响应式容器 */}
      <div style={{ position: 'relative', width: '100%', maxWidth: '1000px', display: 'flex', justifyContent: 'center' }}>
        
        {/* 综合面板 - 内部左右分布 */}
        <div className="hud-panel" style={{ 
          width: '100%', 
          display: 'flex',
          alignItems: 'center',
          gap: '3rem',
          padding: '3rem',
          zIndex: 2
        }}>
          {/* 左侧：代码面板 */}
          <div style={{ flex: 1, position: 'relative' }}>
            {/* 激光扫描线 - 现在平滑移动 */}
            <motion.div 
              style={{
                position: 'absolute',
                left: '-1rem',
                right: '-1rem',
                height: '2px',
                background: 'linear-gradient(90deg, transparent, var(--primary), transparent)',
                boxShadow: '0 0 15px var(--primary)',
                zIndex: 10,
                top: laserTop
              }}
            />

            <div style={{ fontFamily: 'Technical', fontSize: '0.95rem', color: 'var(--text-muted)' }}>
              <div style={{ color: 'var(--primary)', marginBottom: '1.5rem', fontWeight: 'bold' }}>
                <span style={{ marginRight: '10px' }}>▶</span>
                {t('scanner.level')}
              </div>
              <pre style={{ lineHeight: '2', margin: 0 }}>
                {`import { something } from 'lib-noise';`} <br/>
                
                <motion.span style={{ color: highlightColor }}>
                  {`<Select label="Select Language" />`}
                </motion.span> <br/>
                
                {`const x = "简体中文";`} 
                <motion.span style={{ color: 'var(--accent)', opacity: opacityEndonym, marginLeft: '10px' }}>
                  // {t('scanner.blocked')}
                </motion.span> <br/>
                
                {`const y = "Choose...";`} <br/>
                {`export const App = () => { ... }`}
              </pre>
            </div>
          </div>

          {/* 右侧：说明文字 */}
          <div style={{ 
            flex: '0 0 320px',
            textAlign: 'left',
            paddingLeft: '3rem',
            borderLeft: '1px solid var(--line-color)'
          }}>
            <h3 style={{ color: 'var(--primary)', fontFamily: 'Technical', textShadow: '0 0 10px var(--primary-glow)' }}>{t('scanner.title')}</h3>
            <p style={{ fontSize: '0.95rem', color: 'var(--text-muted)', marginTop: '1.2rem', lineHeight: '1.7' }}>
              {t('scanner.desc')}
            </p>
          </div>
        </div>

      </div>
    </section>
  );
};

export default ScannerStation;
