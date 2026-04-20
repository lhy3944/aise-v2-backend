'use client';

import { Slot } from 'radix-ui';
import * as React from 'react';
import {
  Controller,
  FormProvider,
  useFormContext,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
} from 'react-hook-form';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

const Form = FormProvider;

type FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> = {
  name: TName;
};

const FormFieldContext = React.createContext<FormFieldContextValue>({} as FormFieldContextValue);

function FormField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({ ...props }: ControllerProps<TFieldValues, TName>) {
  return (
    <FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  );
}

function useFormField() {
  const fieldContext = React.useContext(FormFieldContext);
  const { getFieldState, formState } = useFormContext();
  const fieldState = getFieldState(fieldContext.name, formState);

  return {
    name: fieldContext.name,
    ...fieldState,
  };
}

type FormItemContextValue = {
  id: string;
};

const FormItemContext = React.createContext<FormItemContextValue>({} as FormItemContextValue);

function FormItem({ className, ...props }: React.ComponentProps<'div'>) {
  const id = React.useId();

  return (
    <FormItemContext.Provider value={{ id }}>
      <div data-slot='form-item' className={cn('space-y-2', className)} {...props} />
    </FormItemContext.Provider>
  );
}

function FormLabel({ className, ...props }: React.ComponentProps<typeof Label>) {
  const { name, error } = useFormField();
  const { id } = React.useContext(FormItemContext);

  return (
    <Label
      className={cn(error && 'text-destructive', className)}
      htmlFor={`${id}-${name}`}
      {...props}
    />
  );
}

function FormControl({ ...props }: React.ComponentProps<typeof Slot.Root>) {
  const { name, error } = useFormField();
  const { id } = React.useContext(FormItemContext);

  return (
    <Slot.Root
      id={`${id}-${name}`}
      aria-invalid={!!error}
      aria-describedby={error ? `${id}-${name}-error` : undefined}
      {...props}
    />
  );
}

function FormDescription({ className, ...props }: React.ComponentProps<'p'>) {
  return <p className={cn('text-fg-muted text-xs', className)} {...props} />;
}

function FormMessage({ className, ...props }: React.ComponentProps<'p'>) {
  const { name, error } = useFormField();
  const { id } = React.useContext(FormItemContext);
  const body = error?.message ?? props.children;

  if (!body) return null;

  return (
    <p
      id={`${id}-${name}-error`}
      className={cn('text-destructive text-xs font-medium', className)}
      role='alert'
      {...props}
    >
      {body}
    </p>
  );
}

export { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage };
