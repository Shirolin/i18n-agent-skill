import { useRef } from 'react';
import { motion } from 'framer-motion';
import { useScrollProgress } from '../hooks/useScrollProgress';

const ScannerStation = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const progress = useScrollProgress(containerRef);

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
      <div style={{ 
        width: '100%', 
        maxWidth: '800px', 
        backgroundColor: 'rgba(255,255,255,0.02)',
        border: '1px solid var(--line-color)',
        borderRadius: '8px',
        padding: '2rem',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* 激光扫描线 */}
        <motion.div 
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            height: '2px',
            background: 'linear-gradient(90deg, transparent, var(--primary), transparent)',
            boxShadow: '0 0 15px var(--primary)',
            zIndex: 10,
            top: `${progress * 100}%`
          }}
        />

        <div style={{ fontFamily: 'Technical', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          <div style={{ color: 'var(--primary)', marginBottom: '1rem' }}>// Level 1: AST X-Ray Scan</div>
          <pre style={{ lineHeight: '1.8' }}>
            {`import { something } from 'lib-noise';`} <br/>
            <span style={{ color: progress > 0.4 ? 'var(--primary)' : 'inherit', transition: 'color 0.3s' }}>
              {`<Select label="Select Language" />`}
            </span> <br/>
            {`const x = "简体中文";`} <span style={{ color: 'var(--accent)', opacity: progress > 0.7 ? 1 : 0 }}>// BLOCKED: ENDONYM</span> <br/>
            {`const y = "Choose...";`} <br/>
            {`export const App = () => { ... }`}
          </pre>
        </div>
      </div>

      <div style={{ 
        position: 'absolute', 
        right: '5%', 
        top: '50%', 
        transform: 'translateY(-50%)',
        textAlign: 'right',
        maxWidth: '300px'
      }}>
        <h3 style={{ color: 'var(--primary)', fontFamily: 'Technical' }}>PRECISION EXTRACTION</h3>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          利用 Tree-sitter AST 深度解析代码上下文。精准识别 UI 属性，自动过滤库路径与数据干扰项。
        </p>
      </div>
    </section>
  );
};

export default ScannerStation;
