import { motion } from 'framer-motion'
import UploadWorkflow from '@/components/Upload/UploadWorkflow'

export default function Upload() {
  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="max-w-4xl space-y-8">
      <UploadWorkflow />
    </motion.div>
  )
}
