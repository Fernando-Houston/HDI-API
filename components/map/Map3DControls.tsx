'use client'

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Building2, 
  Construction, 
  TrendingUp, 
  GraduationCap, 
  Layers3,
  Activity,
  ChevronRight,
  Info
} from 'lucide-react';

interface Map3DControlsProps {
  activeVisualization: string | null;
  onVisualizationChange: (type: string | null) => void;
}

const visualizations = [
  {
    id: 'heatTower',
    name: 'Property Value Towers',
    icon: Building2,
    description: 'See median home values as 3D towers with color-coded appreciation rates',
    color: 'from-blue-500 to-indigo-600',
    insights: '615K median in Heights, 850K in River Oaks'
  },
  {
    id: 'constructionTimeLapse',
    name: 'Construction Activity',
    icon: Construction,
    description: 'Watch development patterns animate over time',
    color: 'from-orange-500 to-red-600',
    insights: '970 residential permits in December 2024'
  },
  {
    id: 'roiTopography',
    name: 'ROI Topography',
    icon: TrendingUp,
    description: 'Explore investment returns as a 3D terrain map',
    color: 'from-green-500 to-emerald-600',
    insights: 'Peak ROI 15.2% in EaDo area'
  },
  {
    id: 'schoolImpact',
    name: 'School Impact Zones',
    icon: GraduationCap,
    description: 'See how school ratings affect property values',
    color: 'from-purple-500 to-pink-600',
    insights: 'A-rated schools add up to $100K value'
  },
  {
    id: 'gentrificationLayers',
    name: 'Gentrification Risk',
    icon: Layers3,
    description: 'View layered analysis of neighborhood changes',
    color: 'from-yellow-500 to-orange-600',
    insights: 'EaDo shows 95% gentrification risk'
  },
  {
    id: 'marketPulse',
    name: 'Real-Time Activity',
    icon: Activity,
    description: 'Live market pulses for new listings and sales',
    color: 'from-cyan-500 to-blue-600',
    insights: '8,588 homes sold in July 2025'
  }
];

export const Map3DControls: React.FC<Map3DControlsProps> = ({ 
  activeVisualization, 
  onVisualizationChange 
}) => {
  const [isExpanded, setIsExpanded] = React.useState(true);
  const [hoveredId, setHoveredId] = React.useState<string | null>(null);
  
  return (
    <motion.div 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="absolute top-24 left-4 z-20 bg-white/95 backdrop-blur-md rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
      style={{ width: isExpanded ? '360px' : '60px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className={`font-semibold text-gray-900 transition-opacity ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
          3D Data Visualizations
        </h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <ChevronRight className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </button>
      </div>
      
      {/* Visualization Options */}
      <div className="p-2">
        <AnimatePresence>
          {visualizations.map((viz, index) => {
            const Icon = viz.icon;
            const isActive = activeVisualization === viz.id;
            const isHovered = hoveredId === viz.id;
            
            return (
              <motion.div
                key={viz.id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="mb-2"
              >
                <button
                  onClick={() => onVisualizationChange(isActive ? null : viz.id)}
                  onMouseEnter={() => setHoveredId(viz.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={`
                    w-full flex items-center gap-3 p-3 rounded-lg transition-all duration-200
                    ${isActive 
                      ? 'bg-gradient-to-r ' + viz.color + ' text-white shadow-lg scale-[1.02]' 
                      : 'bg-gray-50 hover:bg-gray-100 text-gray-700'
                    }
                  `}
                >
                  <div className={`p-2 rounded-lg ${isActive ? 'bg-white/20' : 'bg-white'}`}>
                    <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-gray-600'}`} />
                  </div>
                  
                  {isExpanded && (
                    <div className="flex-1 text-left">
                      <div className="font-medium">{viz.name}</div>
                      {(isActive || isHovered) && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="text-xs mt-1"
                        >
                          <div className={isActive ? 'text-white/90' : 'text-gray-500'}>
                            {viz.description}
                          </div>
                          <div className={`flex items-center gap-1 mt-1 ${isActive ? 'text-white' : 'text-gray-600'}`}>
                            <Info className="w-3 h-3" />
                            <span className="font-medium">{viz.insights}</span>
                          </div>
                        </motion.div>
                      )}
                    </div>
                  )}
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
      
      {/* Legend when active */}
      {activeVisualization && isExpanded && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 border-t border-gray-200 bg-gray-50"
        >
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Data Sources</h4>
          <div className="space-y-1 text-xs text-gray-600">
            <div>• HAR MLS Data (July 2025)</div>
            <div>• Harris County Construction Permits</div>
            <div>• Houston Micro-Market Intelligence</div>
            <div>• School District Impact Analysis</div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};