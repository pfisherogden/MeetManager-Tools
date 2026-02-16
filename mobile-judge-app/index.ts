import { registerRootComponent } from 'expo';
import App from './App';

// registerRootComponent handles both native and web registration automatically
console.log('index.ts: loaded');
try {
  registerRootComponent(App);
  console.log('index.ts: registerRootComponent called');
} catch (e) {
  console.error('index.ts: registerRootComponent failed', e);
}
