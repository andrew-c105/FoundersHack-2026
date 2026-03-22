import { useState } from "react";
import { Link } from "react-router-dom";

interface SignUpFormData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
  acceptTerms: boolean;
}

interface FormErrors {
  firstName?: string;
  lastName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  acceptTerms?: string;
  general?: string;
}

export default function SignUpBlock({ onSuccess, onClose }: { onSuccess: () => void, onClose: () => void }) {
  const [formData, setFormData] = useState<SignUpFormData>({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    confirmPassword: "",
    acceptTerms: false,
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.firstName.trim()) newErrors.firstName = "First name is required";
    if (!formData.lastName.trim()) newErrors.lastName = "Last name is required";
    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address";
    }

    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords don't match";
    }

    if (!formData.acceptTerms) {
      newErrors.acceptTerms = "You must accept the terms and conditions";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: keyof SignUpFormData, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    setIsLoading(true);
    setErrors({});
    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      localStorage.setItem("auth", "true");
      onSuccess();
    } catch (error) {
      setErrors({ general: "An unexpected error occurred. Please try again." });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm mx-auto flex flex-col gap-6 bg-white p-6 md:p-8 rounded-2xl shadow-xl border border-gray-100">
      <div className="text-center">
        <h2 className="text-2xl font-bold font-display text-gray-900">Create Account</h2>
        <p className="mt-1 text-sm text-gray-500">Enter your information to create a new account</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="flex flex-col gap-4">
          {errors.general && (
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {errors.general}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-gray-700" htmlFor="firstName">First Name</label>
              <input
                id="firstName"
                type="text"
                placeholder="John"
                className={`w-full rounded-xl border ${errors.firstName ? 'border-red-300 focus:ring-red-600' : 'border-gray-300 focus:ring-blue-600'} bg-white px-4 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-transparent focus:ring-2 transition`}
                value={formData.firstName}
                onChange={(e) => handleInputChange("firstName", e.target.value)}
                disabled={isLoading}
              />
              {errors.firstName && <p className="text-xs text-red-600">{errors.firstName}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-gray-700" htmlFor="lastName">Last Name</label>
              <input
                id="lastName"
                type="text"
                placeholder="Doe"
                className={`w-full rounded-xl border ${errors.lastName ? 'border-red-300 focus:ring-red-600' : 'border-gray-300 focus:ring-blue-600'} bg-white px-4 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-transparent focus:ring-2 transition`}
                value={formData.lastName}
                onChange={(e) => handleInputChange("lastName", e.target.value)}
                disabled={isLoading}
              />
              {errors.lastName && <p className="text-xs text-red-600">{errors.lastName}</p>}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-gray-700" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="john.doe@example.com"
              className={`w-full rounded-xl border ${errors.email ? 'border-red-300 focus:ring-red-600' : 'border-gray-300 focus:ring-blue-600'} bg-white px-4 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-transparent focus:ring-2 transition`}
              value={formData.email}
              onChange={(e) => handleInputChange("email", e.target.value)}
              disabled={isLoading}
            />
            {errors.email && <p className="text-xs text-red-600">{errors.email}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-gray-700" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="Create a strong password"
              className={`w-full rounded-xl border ${errors.password ? 'border-red-300 focus:ring-red-600' : 'border-gray-300 focus:ring-blue-600'} bg-white px-4 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-transparent focus:ring-2 transition`}
              value={formData.password}
              onChange={(e) => handleInputChange("password", e.target.value)}
              disabled={isLoading}
            />
            {errors.password && <p className="text-xs text-red-600">{errors.password}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-gray-700" htmlFor="confirmPassword">Confirm</label>
            <input
              id="confirmPassword"
              type="password"
              placeholder="Confirm your password"
              className={`w-full rounded-xl border ${errors.confirmPassword ? 'border-red-300 focus:ring-red-600' : 'border-gray-300 focus:ring-blue-600'} bg-white px-4 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-transparent focus:ring-2 transition`}
              value={formData.confirmPassword}
              onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
              disabled={isLoading}
            />
            {errors.confirmPassword && <p className="text-xs text-red-600">{errors.confirmPassword}</p>}
          </div>

          <div className="flex items-center gap-2 mt-2">
            <input
              id="acceptTerms"
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-600"
              checked={formData.acceptTerms}
              onChange={(e) => handleInputChange("acceptTerms", e.target.checked)}
            />
            <label htmlFor="acceptTerms" className="text-xs text-gray-600">
              I agree to the Terms and Conditions
            </label>
          </div>
          {errors.acceptTerms && <p className="text-xs text-red-600 -mt-2">{errors.acceptTerms}</p>}
        </div>

        <div className="flex flex-col gap-4 mt-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-xl bg-blue-600 px-4 py-2.5 font-bold text-white shadow-sm transition hover:bg-blue-700 hover:-translate-y-0.5 disabled:opacity-70 disabled:hover:translate-y-0"
          >
            {isLoading ? "Creating Account..." : "Create Account"}
          </button>
          <div className="text-center">
            <p className="text-xs text-gray-500 font-medium">
              Already have an account?{" "}
              <Link to="#" onClick={(e) => { e.preventDefault(); onClose(); }} className="text-blue-600 font-bold hover:underline">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </form>
    </div>
  );
}
