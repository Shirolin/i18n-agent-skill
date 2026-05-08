import { useRef } from 'react';
import { motion, MotionValue, useTransform } from 'framer-motion';

interface Props {
  scrollProgress: MotionValue<number>;
}

const ScannerStation = ({ scrollProgress }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  
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
      <div style={{ position: 'relative', width: '100%', maxWidth: '1100px', display: 'flex', justifyContent: 'center' }}>
        
        {/* 代码面板 - 绝对居中 */}
        <div className="hud-panel" style={{ 
          width: '100%', 
          maxWidth: '700px', 
          padding: '2.5rem',
          zIndex: 2
        }}>
          {/* 激光扫描线 - 现在平滑移动 */}
          <motion.div 
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
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
              Level 1: AST X-Ray Scan
            </div>
            <pre style={{ lineHeight: '2' }}>
              {`import { something } from 'lib-noise';`} <br/>
              
              <motion.span style={{ color: highlightColor }}>
                {`<Select label="Select Language" />`}
              </motion.span> <br/>
              
              {`const x = "简体中文";`} 
              <motion.span style={{ color: 'var(--accent)', opacity: opacityEndonym, marginLeft: '10px' }}>
                // BLOCKED: ENDONYM
              </motion.span> <br/>
              
              {`const y = "Choose...";`} <br/>
              {`export const App = () => { ... }`}
            </pre>
          </div>
        </div>

        {/* 说明文字 - 限制在容器内靠右浮动 */}
        <div style={{ 
          position: 'absolute', 
          right: '20px', 
          top: '50%', 
          transform: 'translateY(-50%)',
          textAlign: 'right',
          maxWidth: '300px',
          zIndex: 1
        }}>
          <h3 style={{ color: 'var(--primary)', fontFamily: 'Technical', textShadow: '0 0 10px var(--primary-glow)' }}>PRECISION EXTRACTION</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '1rem', lineHeight: '1.6' }}>
            利用 Tree-sitter AST 深度解析代码上下文。精准识别 UI 属性，自动过滤库路径与数据干扰项。
          </p>
        </div>

      </div>
    </section>
  );
};

export default ScannerStation;
