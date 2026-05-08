import { useState, useEffect } from 'react';

export const useScrollProgress = (ref: React.RefObject<HTMLElement | null>) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      if (!ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      
      // 当组件进入视口时开始计算进度 (0 to 1)
      const start = rect.top - windowHeight;
      const totalHeight = rect.height + windowHeight;
      const current = -start;
      
      const p = Math.min(Math.max(current / totalHeight, 0), 1);
      setProgress(p);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [ref]);

  return progress;
};
