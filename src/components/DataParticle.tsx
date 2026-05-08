import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const CHARS = ['{', '}', '[', ']', 't(', '"', "'", 'i18n', 'key', ';', '=>'];

const DataParticle = () => {
  const [particles, setParticles] = useState<any[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setParticles(prev => [
        ...prev.slice(-15), // 保持池子大小，防止性能问题
        {
          id: Math.random(),
          char: CHARS[Math.floor(Math.random() * CHARS.length)],
          x: (Math.random() - 0.5) * 100 // 漏斗扩散范围
        }
      ]);
    }, 400);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      left: '50%',
      width: '0',
      height: 0,
      zIndex: 2,
      pointerEvents: 'none'
    }}>
      <AnimatePresence>
        {particles.map(p => (
          <motion.div
            key={p.id}
            initial={{ opacity: 0, y: -20, x: p.x }}
            animate={{ 
              opacity: [0, 1, 1, 0],
              y: 500, // 滑落距离
              x: 0, // 最终汇聚到逻辑线
              scale: [1, 1.2, 0.8]
            }}
            exit={{ opacity: 0 }}
            transition={{ duration: 3, ease: "linear" }}
            style={{
              position: 'absolute',
              color: 'var(--line-color)',
              fontFamily: 'Technical',
              fontSize: '0.8rem',
              whiteSpace: 'nowrap'
            }}
          >
            {p.char}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default DataParticle;
