import { useRef } from 'react';
import { motion } from 'framer-motion';
import { Shield, Lock } from 'lucide-react';
import { useScrollProgress } from '../hooks/useScrollProgress';

const PrivacyPool = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const progress = useScrollProgress(containerRef);

  return (
    <section ref={containerRef} style={{ height: '120vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      <div style={{ textAlign: 'left', maxWidth: '400px', position: 'absolute', left: '10%' }}>
        <h3 style={{ color: 'var(--accent)', fontFamily: 'Technical', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Shield size={20} /> PRIVACY DECONTAMINATION
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          内置隐私护盾，自动拦截敏感数据。在文本离开本地环境前，API Keys 和个人隐私已完成 100% 脱敏。
        </p>
      </div>

      <div style={{
        width: '300px',
        height: '400px',
        border: '2px solid var(--accent)',
        borderRadius: '20px',
        background: 'rgba(210, 153, 34, 0.05)',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}>
        {/* 脱敏动效区 */}
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{ fontSize: '0.8rem', fontFamily: 'Technical', color: 'var(--accent)' }}
        >
          {progress > 0.5 ? '[MASKED_API_KEY]' : 'sk-proj-a1b2c3d4e5f6...'}
        </motion.div>
        <Lock size={40} color="var(--accent)" style={{ marginTop: '1rem', opacity: progress > 0.5 ? 1 : 0.2 }} />
      </div>
    </section>
  );
};

export default PrivacyPool;
