import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {DeepEvalCard} from '../src/DeepEvalCard.mjs';

test('AI Quality Evaluation card displays the GEval score, verdict, and reason',()=>{
  const html=renderToStaticMarkup(React.createElement(DeepEvalCard,{
    evaluation:{status:'success',metric_name:'Property Recommendation Quality',score:0.84,verdict:'Meets quality threshold',reason:'Grounded in the retrieved comparable sales.'},
  }));
  assert.match(html,/AI QUALITY EVALUATION/);
  assert.match(html,/Property Recommendation Quality/);
  assert.match(html,/84%/);
  assert.match(html,/Meets quality threshold/);
  assert.match(html,/Grounded in the retrieved comparable sales\./);
});

test('AI Quality Evaluation card reports unavailable without inventing a score',()=>{
  const html=renderToStaticMarkup(React.createElement(DeepEvalCard,{
    evaluation:{status:'unavailable',score:null,verdict:'Evaluation unavailable',reason:'DeepEval could not complete this evaluation (TimeoutError).'},
  }));
  assert.match(html,/Evaluation unavailable/);
  assert.match(html,/—/);
  assert.match(html,/TimeoutError/);
  assert.doesNotMatch(html,/NaN/);
});
