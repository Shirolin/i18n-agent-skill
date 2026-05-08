import { useEffect, useState } from 'react';
import { motion, MotionValue, useTransform } from 'framer-motion';

const CHARS = ['{', '}', '[', ']', 't(', '"', "'", 'i18n', 'key', ';', '=>'];

interface ParticleProps {
  scrollProgress: MotionValue<number>;
}

const DataParticle = ({ scrollProgress }: ParticleProps) => {
  const [particles, setParticles] = useState<any[]>([]);

  useEffect(() => {
    // 持续生成全局粒子
    const interval = setInterval(() => {
      setParticles(prev => {
        // 控制全局粒子数量
        const next = [...prev, {
          id: Math.random(),
          char: CHARS[Math.floor(Math.random() * CHARS.length)],
          xOffset: (Math.random() - 0.5) * 60, // 导管附近的随机偏移
          speed: 1 + Math.random() * 2 // 下落速度因子
        }];
        return next.length > 30 ? next.slice(next.length - 30) : next;
      });
    }, 300);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: '50%',
      width: 0,
      height: '100vh',
      zIndex: 2,
      pointerEvents: 'none'
    }}>
      {particles.map(p => {
        // 利用 useTransform 让粒子随着滚动向下疾驰
        // 当页面向下滚动时，粒子的 top 值增加
        const yPos = useTransform(scrollProgress, [0, 1], ['-10vh', `${100 + p.speed * 50}vh`]);
        const opacity = useTransform(scrollProgress, [0, 0.1, 0.9, 1], [0, 0.6, 0.6, 0]);

        return (
          <motion.div
            key={p.id}
            style={{
              position: 'absolute',
              top: yPos,
              x: p.xOffset,
              opacity: opacity,
              color: 'var(--primary)',
              textShadow: '0 0 8px var(--primary-glow)',
              fontFamily: 'Technical',
              fontSize: '0.85rem',
              whiteSpace: 'nowrap',
              filter: 'blur(0.5px)'
            }}
          >
            {p.char}
          </motion.div>
        );
      })}
    </div>
  );
};

export default DataParticle;
