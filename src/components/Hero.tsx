import { motion } from 'framer-motion';

const Hero = () => {
  return (
    <section style={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      textAlign: 'center',
      padding: '0 2rem'
    }}>
      <motion.h1 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        style={{ 
          fontFamily: 'Technical', 
          fontSize: 'clamp(2rem, 5vw, 4rem)', 
          color: 'var(--primary)',
          marginBottom: '1rem',
          textTransform: 'uppercase',
          letterSpacing: '0.15em'
        }}
      >
        Industrial-Grade<br/>I18n Lifecycle Engine
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 1 }}
        style={{ 
          maxWidth: '600px', 
          color: 'var(--text-muted)',
          fontSize: '1.1rem',
          lineHeight: '1.6',
          marginBottom: '3rem'
        }}
      >
        为规模化项目而生。高精度 AST 提取，内置隐私护盾，驱动国际化从“搜索”向“进化”跃迁。
      </motion.p>

      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.8 }}
        style={{ display: 'flex', gap: '1rem' }}
      >
        <button style={{
          padding: '0.8rem 2rem',
          backgroundColor: 'var(--primary)',
          color: 'var(--bg)',
          border: 'none',
          fontWeight: 'bold',
          cursor: 'pointer',
          borderRadius: '4px',
          fontFamily: 'Technical'
        }}>
          GET STARTED
        </button>
        <button style={{
          padding: '0.8rem 2rem',
          backgroundColor: 'transparent',
          color: 'var(--primary)',
          border: '1px solid var(--primary)',
          fontWeight: 'bold',
          cursor: 'pointer',
          borderRadius: '4px',
          fontFamily: 'Technical'
        }}>
          DOCUMENTATION
        </button>
      </motion.div>
    </section>
  );
};

export default Hero;
