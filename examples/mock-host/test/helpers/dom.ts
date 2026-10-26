/** Disable network navigation only; browser CSP is verified in a real browser. */
export function disableFrameNavigation(): () => void {
  const api: unknown = Reflect.get(window, 'happyDOM');
  if (typeof api !== 'object' || api === null || !('settings' in api)) {
    throw new Error('missing happy-dom settings');
  }
  const settings = api.settings;
  if (typeof settings !== 'object' || settings === null || !('navigation' in settings)) {
    throw new Error('missing navigation settings');
  }
  const navigation = settings.navigation;
  if (
    typeof navigation !== 'object' ||
    navigation === null ||
    !('disableChildFrameNavigation' in navigation) ||
    typeof navigation.disableChildFrameNavigation !== 'boolean'
  ) {
    throw new Error('missing frame setting');
  }
  const previous = navigation.disableChildFrameNavigation;
  navigation.disableChildFrameNavigation = true;
  return () => {
    navigation.disableChildFrameNavigation = previous;
  };
}
