import { render, screen } from '@testing-library/react'
import React from 'react'
import { expect, test } from 'vitest'

test('Example Component', () => {
  render(React.createElement('div', null, 'Hello World'))
  expect(screen.getByText('Hello World')).toBeDefined()
})
