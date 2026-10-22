import React from 'react';
import Plot from 'react-plotly.js';
import Plotly from 'plotly.js-dist-min';
import { DARK_PLOT_LAYOUT } from '../utils/constants';

// Create Plotly component from dist-min
const PlotlyComponent = Plot.default ? Plot.default : Plot;

export const PlotlyChart = ({ data = [], layout = {}, config = {}, style = {}, className = '' }) => {
  const mergedLayout = {
    ...DARK_PLOT_LAYOUT,
    ...layout,
    autosize: true,
  };

  const defaultConfig = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: [
      'lasso2d',
      'select2d',
      'toggleSpikelines',
      'hoverClosestCartesian',
      'hoverCompareCartesian',
    ],
    toImageButtonOptions: {
      format: 'png',
      filename: 'mcx_gold_rva_chart',
      height: 600,
      width: 1000,
      scale: 2,
    },
    ...config,
  };

  return (
    <div className={`w-full overflow-hidden ${className}`}>
      <PlotlyComponent
        data={data}
        layout={mergedLayout}
        config={defaultConfig}
        useResizeHandler={true}
        style={{ width: '100%', height: `${mergedLayout.height || 320}px`, ...style }}
      />
    </div>
  );
};
